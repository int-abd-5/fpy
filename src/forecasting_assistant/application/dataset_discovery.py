from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import UUID

from forecasting_assistant.application.dataset_query import query_from_specification
from forecasting_assistant.application.dataset_ranking import DatasetRanker, ranking_sort_key
from forecasting_assistant.application.dataset_validation import validate_dataset_payload
from forecasting_assistant.domain.datasets import (
    AcquisitionMode,
    CatalogClass,
    DatasetCandidate,
    DatasetSearchQuery,
    DatasetSelection,
    DatasetVersion,
    RankedDatasetCandidate,
    SelectionStatus,
    SourcePlan,
)
from forecasting_assistant.domain.models import ForecastingSpecification
from forecasting_assistant.infrastructure.datasets.object_store import ContentAddressedObjectStore
from forecasting_assistant.infrastructure.datasets.protocol import (
    DatasetCatalogRepository,
    DatasetSourceAdapter,
)


class DatasetPlanNotFoundError(KeyError):
    pass


class DatasetCandidateNotSelectableError(ValueError):
    pass


class DatasetSelectionNotFoundError(KeyError):
    pass


_EXECUTABLE_SUFFIXES = {".bat", ".cmd", ".com", ".dll", ".exe", ".msi", ".ps1", ".sh"}
_EXECUTABLE_MAGIC = (b"MZ", b"\x7fELF", b"#!", b"\xfe\xed\xfa", b"\xcf\xfa\xed\xfe")


def _validate_fetched_content(content: bytes, *, max_unpacked_bytes: int = 250 * 1024 * 1024) -> None:
    if not content:
        raise ValueError("dataset source returned an empty payload")
    if any(content.startswith(magic) for magic in _EXECUTABLE_MAGIC):
        raise ValueError("dataset payload has executable content")
    if not content.startswith(b"PK\x03\x04"):
        return
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > 10_000:
                raise ValueError("dataset archive contains too many files")
            total = 0
            for member in members:
                total += member.file_size
                path = PurePosixPath(member.filename.replace("\\", "/"))
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("dataset archive contains an unsafe path")
                if path.suffix.casefold() in _EXECUTABLE_SUFFIXES:
                    raise ValueError("dataset archive contains an executable file")
                if total > max_unpacked_bytes:
                    raise ValueError("dataset archive exceeds the unpacked size limit")
    except zipfile.BadZipFile as error:
        raise ValueError("dataset archive is malformed") from error


class DatasetDiscoveryService:
    def __init__(
        self,
        adapters: list[DatasetSourceAdapter],
        repository: DatasetCatalogRepository,
        object_store: ContentAddressedObjectStore,
        ranker: DatasetRanker | None = None,
    ) -> None:
        self._adapters = {adapter.source_id: adapter for adapter in adapters}
        if len(self._adapters) != len(adapters):
            raise ValueError("dataset adapter IDs must be unique")
        self._repository = repository
        self._object_store = object_store
        self._ranker = ranker or DatasetRanker()

    def discover_for_specification(
        self,
        specification: ForecastingSpecification,
        *,
        user_id: str | None = None,
        purpose: CatalogClass = CatalogClass.PRODUCTION,
    ) -> SourcePlan:
        query = query_from_specification(specification, user_id=user_id, purpose=purpose)
        return self.discover(specification.specification_id, query)

    def discover(self, specification_id: UUID, query: DatasetSearchQuery) -> SourcePlan:
        candidates: dict[str, DatasetCandidate] = {}
        source_errors: dict[str, str] = {}
        for source_id, adapter in self._adapters.items():
            try:
                for candidate in adapter.search(query):
                    candidates[candidate.candidate_id] = candidate
                    self._repository.save_candidate(candidate)
            except Exception as error:  # noqa: BLE001 - one source must not fail discovery
                source_errors[source_id] = type(error).__name__

        ranked = [
            (candidate, self._ranker.rank(candidate, query)) for candidate in candidates.values()
        ]
        eligible = sorted(
            (item for item in ranked if item[1].eligible), key=ranking_sort_key
        )
        unavailable = sorted(
            (item for item in ranked if not item[1].eligible), key=ranking_sort_key
        )
        plan = SourcePlan(
            specification_id=specification_id,
            query=query,
            recommendations=[
                RankedDatasetCandidate(candidate=candidate, ranking=ranking)
                for candidate, ranking in eligible[:3]
            ],
            unavailable_alternatives=[
                RankedDatasetCandidate(candidate=candidate, ranking=ranking)
                for candidate, ranking in unavailable[:10]
            ],
            source_errors=source_errors,
        )
        self._repository.save_plan(plan)
        return plan

    def confirm_dataset(
        self,
        plan_id: UUID,
        candidate_id: str,
        *,
        confirm: bool,
        user_id: str | None = None,
    ) -> DatasetSelection:
        if confirm is not True:
            raise ValueError("explicit dataset confirmation is required")
        plan = self._repository.load_plan(plan_id)
        if plan is None:
            raise DatasetPlanNotFoundError(str(plan_id))
        allowed = {item.candidate.candidate_id for item in plan.recommendations}
        if candidate_id not in allowed:
            raise DatasetCandidateNotSelectableError(
                "candidate is not an eligible recommendation in this source plan"
            )
        if plan.query.user_id and user_id != plan.query.user_id:
            raise DatasetCandidateNotSelectableError("dataset plan belongs to a different user scope")
        selection = DatasetSelection(
            plan_id=plan.plan_id,
            specification_id=plan.specification_id,
            candidate_id=candidate_id,
            user_id=user_id,
        )
        self._repository.save_selection(selection)
        return selection

    def fetch_selection(self, selection_id: UUID) -> DatasetVersion:
        selection = self._repository.load_selection(selection_id)
        if selection is None:
            raise DatasetSelectionNotFoundError(str(selection_id))
        if selection.status not in {SelectionStatus.CONFIRMED, SelectionStatus.FETCHED}:
            raise ValueError("dataset selection has not been explicitly confirmed")
        candidate = self._repository.load_candidate(selection.candidate_id)
        if candidate is None:
            raise KeyError("selected dataset candidate no longer exists")
        if candidate.acquisition_mode in {
            AcquisitionMode.DISCOVERY_ONLY,
            AcquisitionMode.REQUEST_REQUIRED,
        }:
            raise ValueError("selected dataset cannot be fetched automatically")

        shared = candidate.license.redistribution_allowed is True
        if not shared and not selection.user_id:
            raise ValueError("non-redistributable or unverified data requires a user scope")
        cache_key = DatasetVersion.cache_identity(candidate, user_id=selection.user_id)
        cached = self._repository.find_cached_version(cache_key, user_id=selection.user_id)
        plan = self._repository.load_plan(selection.plan_id)
        if cached is not None and self._cache_is_fresh(cached, candidate, plan):
            return cached

        try:
            adapter = self._adapters[candidate.adapter_id]
        except KeyError as error:
            raise KeyError("selected dataset adapter is not configured") from error
        result = adapter.fetch(candidate)
        _validate_fetched_content(result.content)
        quality = validate_dataset_payload(
            result.content,
            content_type=result.content_type,
            candidate=candidate,
            query=plan.query if plan is not None else DatasetSearchQuery(target=candidate.title),
        )
        digest, path = self._object_store.put(
            result.content,
            shared=shared,
            user_id=selection.user_id,
        )
        version = DatasetVersion(
            candidate_id=candidate.candidate_id,
            cache_key=cache_key,
            sha256=digest,
            storage_path=str(path),
            byte_size=len(result.content),
            content_type=result.content_type,
            source_version=result.source_version,
            query_identity=candidate.query_identity,
            shared=shared,
            user_id=None if shared else selection.user_id,
            license_snapshot=candidate.license.model_copy(deep=True),
            metadata={**result.metadata, "quality_report": quality.model_dump(mode="json")},
        )
        self._repository.save_version(version)
        selection.status = SelectionStatus.FETCHED
        self._repository.save_selection(selection)
        return version

    def store_derived_version(
        self,
        parent_version_id: UUID,
        content: bytes,
        *,
        content_type: str,
        user_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> DatasetVersion:
        """Store a normalized derivative without overwriting its immutable raw parent."""
        parent = self._repository.load_version(parent_version_id)
        if parent is None:
            raise KeyError("parent dataset version does not exist")
        if not parent.shared and (not user_id or parent.user_id != user_id):
            raise ValueError("private parent dataset belongs to a different user scope")
        _validate_fetched_content(content)
        digest, path = self._object_store.put(
            content,
            shared=parent.shared,
            user_id=None if parent.shared else user_id,
        )
        version = DatasetVersion(
            candidate_id=parent.candidate_id,
            cache_key=f"derived:{parent.version_id}:{digest}",
            sha256=digest,
            storage_path=str(path),
            byte_size=len(content),
            content_type=content_type,
            source_version=parent.source_version,
            query_identity=parent.query_identity,
            shared=parent.shared,
            user_id=None if parent.shared else user_id,
            parent_version_id=parent.version_id,
            license_snapshot=parent.license_snapshot.model_copy(deep=True),
            metadata={"kind": "normalized", **(metadata or {})},
        )
        self._repository.save_version(version)
        return version

    def _cache_is_fresh(
        self,
        version: DatasetVersion,
        candidate: DatasetCandidate,
        plan: SourcePlan | None,
    ) -> bool:
        if candidate.metadata.get("immutable") is True:
            return True
        configured_days = plan.query.maximum_staleness_days if plan else None
        if configured_days is not None:
            ttl = timedelta(days=configured_days)
        elif candidate.acquisition_mode == AcquisitionMode.API:
            ttl = timedelta(days=1)
        else:
            ttl = timedelta(days=30)
        retrieved_at = version.retrieved_at
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - retrieved_at <= ttl
