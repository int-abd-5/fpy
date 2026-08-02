from __future__ import annotations

from typing import Any

import pytest

from forecasting_assistant.domain.datasets import DatasetSearchQuery
from forecasting_assistant.infrastructure.datasets.adapters import (
    PMDWIS2Adapter,
    WHOGHOAdapter,
    pakistan_catalog_adapters,
    research_catalog_adapter,
)
from forecasting_assistant.infrastructure.datasets.http import (
    UnsafeDatasetUrlError,
    validate_public_https_url,
)


class FakeHttp:
    def __init__(self, payload: Any = None) -> None:
        self.payload = payload

    def get_json(self, url: str, *, headers: dict[str, str] | None = None) -> Any:
        return self.payload

    def get_bytes(self, url: str, *, headers: dict[str, str] | None = None):
        raise AssertionError("test did not authorize a network fetch")


def test_pmd_wis2_core_metadata_is_production_eligible_input() -> None:
    payload = {
        "features": [
            {
                "id": "daily-climate",
                "properties": {
                    "title": "Daily land station climate observations",
                    "description": "Daily temperature and rainfall observations for Pakistan stations",
                    "wmo:dataPolicy": "core",
                },
                "links": [
                    {
                        "rel": "data",
                        "href": "https://wis2box.pmd.gov.pk/oapi/collections/messages/items?f=json",
                    }
                ],
            }
        ]
    }
    adapter = PMDWIS2Adapter(FakeHttp(payload))

    candidates = adapter.search(
        DatasetSearchQuery(
            target="daily temperature",
            geography=["Pakistan"],
            frequency="daily",
        )
    )

    assert len(candidates) == 1
    assert candidates[0].publisher == "Pakistan Meteorological Department"
    assert candidates[0].license.verified
    assert candidates[0].license.redistribution_allowed is True
    assert candidates[0].metadata["wmo_data_policy"] == "core"


def test_ndma_mhvra_and_open_data_pakistan_are_not_automatic_sources() -> None:
    adapters = pakistan_catalog_adapters(FakeHttp())
    query = DatasetSearchQuery(
        target="Pakistan disaster flood risk",
        geography=["Pakistan"],
    )
    candidates = [candidate for adapter in adapters for candidate in adapter.search(query)]

    mhvra = next(item for item in candidates if item.canonical_identifier == "e-mhvra")
    assert mhvra.acquisition_mode.value == "request_required"
    assert not mhvra.license.verified

    broad_query = DatasetSearchQuery(target="Pakistan government statistics", geography=["Pakistan"])
    broad_candidates = [
        candidate for adapter in adapters for candidate in adapter.search(broad_query)
    ]
    aggregator = next(item for item in broad_candidates if item.adapter_id == "open-data-pakistan")
    assert not aggregator.original_publisher_verified
    assert aggregator.acquisition_mode.value == "discovery_only"


def test_research_catalog_stays_separate() -> None:
    adapter = research_catalog_adapter(FakeHttp())
    results = adapter.search(DatasetSearchQuery(target="time series forecasting benchmark"))

    assert {item.canonical_identifier for item in results} == {"autoforecast", "monash"}
    assert all(item.catalog_class.value == "research" for item in results)
    assert all(item.license.research_only for item in results)


def test_who_adapter_returns_concrete_matching_indicator_endpoint() -> None:
    adapter = WHOGHOAdapter(
        FakeHttp(
            {
                "value": [
                    {
                        "IndicatorCode": "WHOSIS_000001",
                        "IndicatorName": "Life expectancy at birth",
                    },
                    {"IndicatorCode": "OTHER", "IndicatorName": "Unrelated value"},
                ]
            }
        )
    )

    candidates = adapter.search(
        DatasetSearchQuery(
            target="life expectancy health",
            geography=["Pakistan"],
        )
    )

    assert len(candidates) == 1
    assert candidates[0].canonical_identifier == "WHOSIS_000001"
    assert "SpatialDim%20eq%20%27PAK%27" in candidates[0].source_url


def test_secure_url_validation_rejects_private_hosts_credentials_and_executables() -> None:
    public = lambda host, port: ["8.8.8.8"]
    private = lambda host, port: ["127.0.0.1"]

    validate_public_https_url("https://example.com/data.csv", resolver=public)
    with pytest.raises(UnsafeDatasetUrlError, match="HTTPS"):
        validate_public_https_url("http://example.com/data.csv", resolver=public)
    with pytest.raises(UnsafeDatasetUrlError, match="credentials"):
        validate_public_https_url(
            "https://example.com/data.csv?api_key=secret", resolver=public
        )
    with pytest.raises(UnsafeDatasetUrlError, match="private"):
        validate_public_https_url("https://localhost/data.csv", resolver=private)
    with pytest.raises(UnsafeDatasetUrlError, match="executable"):
        validate_public_https_url("https://example.com/data.exe", resolver=public)
