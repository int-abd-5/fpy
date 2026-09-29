from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

from forecasting_assistant.config import Settings
from forecasting_assistant.domain.datasets import (
    AcquisitionMode,
    CatalogClass,
    DatasetCandidate,
    DatasetSearchQuery,
    FetchResult,
    LicenseAssessment,
    QualityReport,
    SourceRole,
)
from forecasting_assistant.infrastructure.datasets.http import DatasetDownloadError
from forecasting_assistant.infrastructure.datasets.protocol import HttpClient
from forecasting_assistant.infrastructure.datasets.registry_client import RegistryClient


class RegistryDatasetAdapter:
    source_id = "data-registry"

    def __init__(self, client: RegistryClient, http: HttpClient, *, settings: Settings) -> None:
        self._client = client
        self._http = http
        self._settings = settings
        self._candidates: dict[str, DatasetCandidate] = {}

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        self._client.health(timeout_seconds=min(self._settings.registry_timeout_seconds, 3.0))
        response = self._client.resolve(self._resolve_payload(query))
        companions = [item for item in response["companion_sources"] if isinstance(item, dict)]
        lineage = response["lineage"]
        warnings = response["warnings"]
        candidates: list[DatasetCandidate] = []
        for source in response["target_sources"]:
            if not isinstance(source, dict):
                continue
            candidate = self._candidate_from_source(source, query, companions, lineage, warnings)
            if candidate is None:
                continue
            self._candidates[candidate.candidate_id] = candidate
            candidates.append(candidate.model_copy(deep=True))
        return candidates

    def describe(self, candidate_id: str) -> DatasetCandidate:
        try:
            return self._candidates[candidate_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError("unknown data-registry dataset candidate") from error

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        endpoint_url = candidate.metadata.get("registry", {}).get("endpoint_url")
        if not isinstance(endpoint_url, str) or not endpoint_url:
            endpoint_url = candidate.source_url
        if not isinstance(endpoint_url, str) or not endpoint_url:
            raise DatasetDownloadError("registry dataset endpoint URL is missing")
        result = self._http.get_bytes(endpoint_url)
        metadata = {
            **result.metadata,
            "registry_slug": candidate.canonical_identifier,
            "fetch_hint": candidate.metadata.get("registry", {}).get("fetch_hint"),
        }
        return result.model_copy(update={"metadata": metadata})

    def _resolve_payload(self, query: DatasetSearchQuery) -> dict[str, Any]:
        target = query.target.strip()
        payload: dict[str, Any] = {
            "prompt": target,
            "min_relevance": self._settings.registry_min_relevance,
            "min_companion_strength": self._settings.registry_min_companion_strength,
            "max_dependency_depth": self._settings.registry_max_dependency_depth,
            "max_sources": self._settings.registry_max_sources,
            "include_pending": (
                self._settings.registry_include_pending and not self._settings.registry_required
            ),
        }
        if "." in target:
            payload["target"] = target
        elif target:
            payload["fields"] = [target]
        if query.geography:
            payload["geo"] = ", ".join(query.geography)
        if query.frequency:
            payload["frequency"] = query.frequency
        return payload

    def _candidate_from_source(
        self,
        source: dict[str, Any],
        query: DatasetSearchQuery,
        companions: list[dict[str, Any]],
        lineage: list[Any],
        warnings: list[Any],
    ) -> DatasetCandidate | None:
        slug = source.get("slug")
        endpoint_url = source.get("endpoint_url")
        if source.get("status") != "verified":
            return None
        if source.get("health") not in {"ok", "unknown"}:
            return None
        if not isinstance(slug, str) or not slug.strip():
            return None
        if not isinstance(endpoint_url, str) or urlsplit(endpoint_url).scheme not in {"http", "https"}:
            return None

        raw_provider = source.get("provider")
        provider: dict[str, Any] = raw_provider if isinstance(raw_provider, dict) else {}
        provider_name = str(provider.get("name") or provider.get("code") or "Registry provider")
        provider_license = provider.get("license") or provider.get("license_name")
        tags = [
            str(item.get("value"))
            for item in source.get("tags", [])
            if isinstance(item, dict) and item.get("value")
        ]
        fields = [
            item
            for item in source.get("fields", [])
            if isinstance(item, dict) and item.get("name")
        ]
        endpoint_type = str(source.get("endpoint_type") or "rest_json").casefold()
        acquisition_mode = (
            AcquisitionMode.DOWNLOAD if endpoint_type in {"csv", "array_csv"} else AcquisitionMode.API
        )
        source_role = (
            SourceRole.AGGREGATOR
            if str(source.get("source_role", "")).casefold() == "aggregator"
            or str(provider.get("role", "")).casefold() == "aggregator"
            else SourceRole.OFFICIAL_SECONDARY
        )
        source_copy = _redact(source)
        metadata = {
            "registry": source_copy,
            "registry_companions": deepcopy(companions),
            "registry_lineage": deepcopy(lineage),
            "registry_warnings": deepcopy(warnings),
        }
        if source.get("health") == "unknown":
            metadata["registry_warnings"].append("registry source health is unknown; fetch validation is required")
        return DatasetCandidate(
            candidate_id=DatasetCandidate.stable_id(self.source_id, slug),
            adapter_id=self.source_id,
            canonical_identifier=slug,
            title=str(source.get("name") or slug),
            description=str(source.get("description") or ""),
            publisher=provider_name,
            source_url=endpoint_url,
            catalog_class=CatalogClass.PRODUCTION,
            source_role=source_role,
            acquisition_mode=acquisition_mode,
            official=True,
            original_publisher_verified=True,
            geography=_source_geography(source, query),
            target_variables=sorted(
                set(tags) | {str(item["name"]) for item in fields}
            ),
            tags=tags,
            unit=_first_field_value(fields, "unit"),
            frequency=_as_optional_string(source.get("frequency")),
            temporal_start=_parse_date(source.get("temporal_start")),
            temporal_end=_parse_date(source.get("temporal_end")),
            release_date=_parse_date(source.get("updated_at")),
            license=LicenseAssessment(
                name=_as_optional_string(provider_license),
                url=_as_optional_string(provider.get("license_url")),
                verified=bool(provider_license),
                restrictions=(
                    ["provider requires credentials"]
                    if provider.get("requires_key")
                    else []
                ),
            ),
            quality=QualityReport(
                human_verified=source.get("status") == "verified",
                warnings=[str(item) for item in warnings if isinstance(item, str)],
            ),
            access_restrictions=(
                ["provider API key required"] if provider.get("requires_key") else []
            ),
            credential_reference=_as_optional_string(provider.get("api_key_env")),
            stable_machine_interface=True,
            query_identity=endpoint_url,
            metadata=metadata,
        )


def _source_geography(source: dict[str, Any], query: DatasetSearchQuery) -> list[str]:
    values = source.get("geography") or source.get("geo")
    if isinstance(values, str):
        return [values]
    if isinstance(values, list):
        return [str(item) for item in values if str(item).strip()]
    return list(query.geography)


def _first_field_value(fields: list[dict[str, Any]], key: str) -> str | None:
    for field in fields:
        value = field.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _as_optional_string(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).casefold()
            if any(secret in normalized for secret in ("secret", "password", "token", "authorization")):
                result[key] = "[redacted]"
            else:
                result[key] = _redact(item)
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
