from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from forecasting_assistant.application.dataset_discovery import DatasetDiscoveryService
from forecasting_assistant.domain.datasets import (
    AcquisitionMode,
    CatalogClass,
    DatasetCandidate,
    DatasetSearchQuery,
    DatasetSelection,
    DatasetVersion,
    FetchResult,
    LicenseAssessment,
    SourcePlan,
    SourceRole,
)
from forecasting_assistant.infrastructure.datasets.object_store import ContentAddressedObjectStore


class MemoryCatalogRepository:
    def __init__(self) -> None:
        self.candidates: dict[str, DatasetCandidate] = {}
        self.plans: dict[UUID, SourcePlan] = {}
        self.selections: dict[UUID, DatasetSelection] = {}
        self.versions: list[DatasetVersion] = []

    def initialize(self) -> None:
        return

    def save_candidate(self, candidate: DatasetCandidate) -> None:
        self.candidates[candidate.candidate_id] = candidate.model_copy(deep=True)

    def load_candidate(self, candidate_id: str) -> DatasetCandidate | None:
        return deepcopy(self.candidates.get(candidate_id))

    def save_plan(self, plan: SourcePlan) -> None:
        self.plans[plan.plan_id] = plan.model_copy(deep=True)

    def load_plan(self, plan_id: UUID) -> SourcePlan | None:
        return deepcopy(self.plans.get(plan_id))

    def save_selection(self, selection: DatasetSelection) -> None:
        self.selections[selection.selection_id] = selection.model_copy(deep=True)

    def load_selection(self, selection_id: UUID) -> DatasetSelection | None:
        return deepcopy(self.selections.get(selection_id))

    def save_version(self, version: DatasetVersion) -> None:
        self.versions.append(version.model_copy(deep=True))

    def load_version(self, version_id: UUID) -> DatasetVersion | None:
        return next(
            (item.model_copy(deep=True) for item in self.versions if item.version_id == version_id),
            None,
        )

    def find_cached_version(
        self, cache_key: str, *, user_id: str | None
    ) -> DatasetVersion | None:
        for version in reversed(self.versions):
            if version.cache_key == cache_key and (version.shared or version.user_id == user_id):
                return version.model_copy(deep=True)
        return None


class FakeAdapter:
    def __init__(
        self,
        source_id: str,
        candidates: list[DatasetCandidate],
        *,
        content: bytes = b"date,value\n" + b"2026-01-01,1\n" * 30,
        fail_search: bool = False,
    ) -> None:
        self.source_id = source_id
        self.candidates = {item.candidate_id: item for item in candidates}
        self.content = content
        self.fail_search = fail_search
        self.fetch_count = 0

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        if self.fail_search:
            raise RuntimeError("provider unavailable")
        return list(self.candidates.values())

    def describe(self, candidate_id: str) -> DatasetCandidate:
        return self.candidates[candidate_id]

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        self.fetch_count += 1
        return FetchResult(content=self.content, content_type="text/csv")


def _candidate(
    source_id: str,
    identifier: str,
    *,
    redistribution: bool = True,
    mode: AcquisitionMode = AcquisitionMode.API,
) -> DatasetCandidate:
    return DatasetCandidate(
        candidate_id=DatasetCandidate.stable_id(source_id, identifier),
        adapter_id=source_id,
        canonical_identifier=identifier,
        title=f"Official temperature {identifier}",
        publisher="Official agency",
        source_url=f"https://example.com/{identifier}",
        catalog_class=CatalogClass.PRODUCTION,
        source_role=SourceRole.PRIMARY,
        acquisition_mode=mode,
        official=True,
        original_publisher_verified=True,
        geography=["Pakistan"],
        target_variables=["temperature"],
        frequency="daily",
        license=LicenseAssessment(
            name="test",
            verified=True,
            commercial_use_allowed=True,
            redistribution_allowed=redistribution,
        ),
        stable_machine_interface=True,
    )


def _service(
    tmp_path: Path, adapters: list[FakeAdapter]
) -> tuple[DatasetDiscoveryService, MemoryCatalogRepository]:
    repository = MemoryCatalogRepository()
    service = DatasetDiscoveryService(
        adapters,
        repository,
        ContentAddressedObjectStore(tmp_path / "objects"),
    )
    return service, repository


def test_discovery_returns_only_top_three_and_isolates_adapter_failures(tmp_path: Path) -> None:
    candidates = [_candidate("good", str(index)) for index in range(5)]
    service, _ = _service(
        tmp_path,
        [FakeAdapter("good", candidates), FakeAdapter("broken", [], fail_search=True)],
    )

    plan = service.discover(
        uuid4(),
        DatasetSearchQuery(
            target="temperature", geography=["Pakistan"], frequency="daily"
        ),
    )

    assert len(plan.recommendations) == 3
    assert plan.source_errors == {"broken": "RuntimeError"}
    assert all(item.ranking.eligible for item in plan.recommendations)


def test_selection_requires_explicit_confirmation_and_recommended_candidate(
    tmp_path: Path,
) -> None:
    candidate = _candidate("official", "temperature")
    service, _ = _service(tmp_path, [FakeAdapter("official", [candidate])])
    plan = service.discover(
        uuid4(),
        DatasetSearchQuery(target="temperature", geography=["Pakistan"], frequency="daily"),
    )

    with pytest.raises(ValueError, match="explicit"):
        service.confirm_dataset(plan.plan_id, candidate.candidate_id, confirm=False)
    with pytest.raises(ValueError, match="eligible recommendation"):
        service.confirm_dataset(plan.plan_id, "not-ranked", confirm=True)


def test_shared_cache_is_reused_after_confirmed_selection(tmp_path: Path) -> None:
    candidate = _candidate("official", "temperature")
    adapter = FakeAdapter("official", [candidate])
    service, _ = _service(tmp_path, [adapter])
    plan = service.discover(
        uuid4(),
        DatasetSearchQuery(target="temperature", geography=["Pakistan"], frequency="daily"),
    )
    selection = service.confirm_dataset(plan.plan_id, candidate.candidate_id, confirm=True)

    first = service.fetch_selection(selection.selection_id)
    second = service.fetch_selection(selection.selection_id)

    assert first == second
    assert first.shared
    assert adapter.fetch_count == 1
    assert Path(first.storage_path).read_bytes() == adapter.content


def test_nonredistributable_data_is_user_scoped_and_not_cross_tenant(tmp_path: Path) -> None:
    candidate = _candidate("private", "temperature", redistribution=False)
    adapter = FakeAdapter("private", [candidate])
    service, repository = _service(tmp_path, [adapter])
    plan_a = service.discover(
        uuid4(),
        DatasetSearchQuery(
            target="temperature",
            geography=["Pakistan"],
            frequency="daily",
            user_id="user-a",
        ),
    )
    selection_a = service.confirm_dataset(
        plan_a.plan_id, candidate.candidate_id, confirm=True, user_id="user-a"
    )
    version_a = service.fetch_selection(selection_a.selection_id)
    assert not version_a.shared
    assert version_a.user_id == "user-a"

    cache_key_b = DatasetVersion.cache_identity(candidate, user_id="user-b")
    assert repository.find_cached_version(cache_key_b, user_id="user-b") is None


def test_executable_payload_fails_before_object_storage(tmp_path: Path) -> None:
    candidate = _candidate("unsafe", "temperature")
    service, _ = _service(
        tmp_path, [FakeAdapter("unsafe", [candidate], content=b"MZ executable")]
    )
    plan = service.discover(
        uuid4(),
        DatasetSearchQuery(target="temperature", geography=["Pakistan"], frequency="daily"),
    )
    selection = service.confirm_dataset(plan.plan_id, candidate.candidate_id, confirm=True)

    with pytest.raises(ValueError, match="executable"):
        service.fetch_selection(selection.selection_id)


@pytest.mark.parametrize(
    ("content", "content_type", "message"),
    [
        (b"<html>login</html>", "text/html", "HTML"),
        (b"{not-json", "application/json", "malformed"),
        (b"date,value\n2026-01-01,1\n", "text/csv", "training points"),
    ],
)
def test_invalid_or_inadequate_dataset_payloads_fail_closed(
    tmp_path: Path, content: bytes, content_type: str, message: str
) -> None:
    candidate = _candidate("invalid", "temperature")
    adapter = FakeAdapter("invalid", [candidate], content=content)

    def fetch_with_type(selected: DatasetCandidate) -> FetchResult:
        adapter.fetch_count += 1
        return FetchResult(content=adapter.content, content_type=content_type)

    adapter.fetch = fetch_with_type  # type: ignore[method-assign]
    service, _ = _service(tmp_path, [adapter])
    plan = service.discover(
        uuid4(),
        DatasetSearchQuery(target="temperature", geography=["Pakistan"], frequency="daily"),
    )
    selection = service.confirm_dataset(plan.plan_id, candidate.candidate_id, confirm=True)

    with pytest.raises(ValueError, match=message):
        service.fetch_selection(selection.selection_id)


def test_normalized_derivative_preserves_raw_parent_lineage(tmp_path: Path) -> None:
    candidate = _candidate("official", "temperature")
    adapter = FakeAdapter("official", [candidate])
    service, _ = _service(tmp_path, [adapter])
    plan = service.discover(
        uuid4(),
        DatasetSearchQuery(target="temperature", geography=["Pakistan"], frequency="daily"),
    )
    selection = service.confirm_dataset(plan.plan_id, candidate.candidate_id, confirm=True)
    raw = service.fetch_selection(selection.selection_id)

    normalized = service.store_derived_version(
        raw.version_id,
        b"date,value\n" + b"2026-01-01,1\n" * 30,
        content_type="text/csv",
        metadata={"transform": "canonical-column-names"},
    )

    assert normalized.parent_version_id == raw.version_id
    assert normalized.metadata["kind"] == "normalized"
    assert normalized.metadata["transform"] == "canonical-column-names"
    assert normalized.version_id != raw.version_id
    assert normalized.storage_path == raw.storage_path
