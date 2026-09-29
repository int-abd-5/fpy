from __future__ import annotations

from typing import Any

from forecasting_assistant.config import Settings
from forecasting_assistant.domain.datasets import DatasetSearchQuery, FetchResult
from forecasting_assistant.infrastructure.datasets.registry import build_default_adapters
from forecasting_assistant.infrastructure.datasets.registry_adapter import RegistryDatasetAdapter


def _source(
    slug: str,
    *,
    status: str = "verified",
    health: str = "ok",
    endpoint_url: str | None = "https://data.example.com/bitcoin.json",
) -> dict[str, Any]:
    return {
        "slug": slug,
        "name": "Bitcoin daily prices",
        "description": "A trusted daily Bitcoin price series.",
        "provider": {
            "code": "EXAMPLE",
            "name": "Example Data Provider",
            "license": "Open Data Terms",
            "requires_key": False,
        },
        "endpoint_url": endpoint_url,
        "endpoint_type": "rest_json",
        "status": status,
        "health": health,
        "frequency": "daily",
        "last_checked_at": "2026-09-28T12:00:00+00:00",
        "last_validated_at": "2026-09-28T12:00:00+00:00",
        "updated_at": "2026-09-28T12:00:00+00:00",
        "remote_last_updated": "2026-09-28T11:59:00Z",
        "tags": [
            {"kind": "domain", "value": "finance", "confidence": 1.0, "method": "manual"},
            {"kind": "field", "value": "finance.bitcoin", "confidence": 1.0, "method": "manual"},
        ],
        "matched_tags": [{"kind": "field", "value": "finance.bitcoin", "weight": 1.0}],
        "hierarchy_paths": [["finance"], ["finance", "finance.bitcoin"]],
        "fields": [{"name": "close", "dtype": "number", "unit": "USD"}],
        "fetch_hint": {"sampler": "example_json", "note": "GET the endpoint_url"},
        "relevance_score": 0.91,
        "score": 0.91,
    }


class FakeRegistryClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.payloads: list[dict[str, Any]] = []

    def health(self, *, timeout_seconds: float | None = None) -> dict[str, Any]:
        return {"status": "ok", "db_ok": True}

    def resolve(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        return self.response


class FakeHttp:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def get_bytes(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResult:
        self.urls.append(url)
        return FetchResult(
            content=b'{"date":"2026-09-28","close":65000}',
            content_type="application/json",
            source_version="etag-1",
        )

    def get_json(self, url: str, *, headers: dict[str, str] | None = None) -> Any:
        raise AssertionError("registry adapter should use the registry client for JSON calls")


def test_search_maps_verified_target_source_and_companion_metadata() -> None:
    client = FakeRegistryClient(
        {
            "target_sources": [_source("bitcoin-daily")],
            "companion_sources": [
                {
                    "slug": "fed-funds",
                    "field": "macro.interest_rate",
                    "relation_type": "correlates_with",
                    "matched_via": "finance.bitcoin",
                    "dependency_score": 0.64,
                    "prior_strength": 0.40,
                    "evidence_type": "curated_prior",
                    "depth": 1,
                    "note": "Liquidity context",
                }
            ],
            "lineage": [{"source": "curated"}],
            "warnings": ["dependency scores are not causal proof"],
        }
    )
    adapter = RegistryDatasetAdapter(client, FakeHttp(), settings=Settings(_env_file=None))

    candidates = adapter.search(
        DatasetSearchQuery(target="finance.bitcoin", geography=["global"], frequency="daily")
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.canonical_identifier == "bitcoin-daily"
    assert candidate.source_url == "https://data.example.com/bitcoin.json"
    assert candidate.publisher == "Example Data Provider"
    assert candidate.metadata["registry"]["slug"] == "bitcoin-daily"
    assert candidate.metadata["registry_companions"][0]["dependency_score"] == 0.64
    assert candidate.metadata["registry_lineage"] == [{"source": "curated"}]
    assert candidate.metadata["registry_warnings"] == ["dependency scores are not causal proof"]


def test_search_omits_pending_retired_unhealthy_or_url_less_sources() -> None:
    valid_unknown = _source("unknown-health", health="unknown")
    response = {
        "target_sources": [
            valid_unknown,
            _source("pending", status="pending_review"),
            _source("retired", status="retired"),
            _source("failing", health="failing"),
            _source("missing-url", endpoint_url=None),
        ],
        "companion_sources": [],
        "lineage": [],
        "warnings": [],
    }
    adapter = RegistryDatasetAdapter(
        FakeRegistryClient(response), FakeHttp(), settings=Settings(_env_file=None)
    )

    candidates = adapter.search(DatasetSearchQuery(target="bitcoin"))

    assert [candidate.canonical_identifier for candidate in candidates] == ["unknown-health"]


def test_search_builds_explicit_resolve_payload_from_query() -> None:
    client = FakeRegistryClient(
        {"target_sources": [], "companion_sources": [], "lineage": [], "warnings": []}
    )
    settings = Settings(
        _env_file=None,
        registry_min_relevance=0.85,
        registry_min_companion_strength=0.70,
        registry_max_dependency_depth=3,
        registry_max_sources=7,
        registry_include_pending=True,
        registry_required=True,
    )
    adapter = RegistryDatasetAdapter(client, FakeHttp(), settings=settings)

    adapter.search(
        DatasetSearchQuery(
            target="inflation",
            geography=["Pakistan"],
            frequency="monthly",
        )
    )

    assert client.payloads == [
        {
            "prompt": "inflation",
            "fields": ["inflation"],
            "geo": "Pakistan",
            "frequency": "monthly",
            "min_relevance": 0.85,
            "min_companion_strength": 0.70,
            "max_dependency_depth": 3,
            "max_sources": 7,
            "include_pending": False,
        }
    ]


def test_fetch_uses_secure_http_client_and_preserves_registry_metadata() -> None:
    source = _source("bitcoin-daily")
    client = FakeRegistryClient(
        {"target_sources": [source], "companion_sources": [], "lineage": [], "warnings": []}
    )
    http = FakeHttp()
    adapter = RegistryDatasetAdapter(client, http, settings=Settings(_env_file=None))
    candidate = adapter.search(DatasetSearchQuery(target="bitcoin"))[0]

    result = adapter.fetch(candidate)

    assert http.urls == [source["endpoint_url"]]
    assert result.content_type == "application/json"
    assert result.metadata["registry_slug"] == "bitcoin-daily"
    assert result.metadata["fetch_hint"] == source["fetch_hint"]


def test_describe_returns_cached_candidate_by_stable_registry_slug() -> None:
    client = FakeRegistryClient(
        {"target_sources": [_source("bitcoin-daily")], "companion_sources": [], "lineage": [], "warnings": []}
    )
    adapter = RegistryDatasetAdapter(client, FakeHttp(), settings=Settings(_env_file=None))
    candidate = adapter.search(DatasetSearchQuery(target="bitcoin"))[0]

    described = adapter.describe(candidate.candidate_id)

    assert described == candidate
    assert described is not candidate


def test_configured_registry_replaces_remote_catalog_adapters_but_keeps_local_uploads() -> None:
    settings = Settings(_env_file=None, registry_api_url="https://registry.example.com")

    adapters = build_default_adapters(FakeHttp(), settings=settings)

    assert {adapter.source_id for adapter in adapters} == {"local-upload", "data-registry"}
