from __future__ import annotations

from dataclasses import dataclass

from forecasting_assistant.infrastructure.datasets.adapters import (
    LocalUploadAdapter,
    NASAPowerAdapter,
    PMDWIS2Adapter,
    WHOGHOAdapter,
    WorldBankAdapter,
    international_catalog_adapters,
    pakistan_catalog_adapters,
    research_catalog_adapter,
)
from forecasting_assistant.infrastructure.datasets.protocol import DatasetSourceAdapter, HttpClient


@dataclass(frozen=True)
class ApprovedFutureSource:
    source_id: str
    publisher: str
    catalog_url: str
    intended_use: str


APPROVED_FUTURE_SOURCES = (
    ApprovedFutureSource(
        "imf",
        "International Monetary Fund",
        "https://www.imf.org/external/datamapper/api/",
        "international macroeconomic indicators",
    ),
    ApprovedFutureSource(
        "oecd",
        "Organisation for Economic Co-operation and Development",
        "https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html",
        "international economic and social indicators",
    ),
    ApprovedFutureSource(
        "eurostat",
        "Eurostat",
        "https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction",
        "European official statistics",
    ),
    ApprovedFutureSource(
        "copernicus",
        "Copernicus Climate Change Service",
        "https://climate.copernicus.eu/climate-data-store",
        "climate and reanalysis data",
    ),
    ApprovedFutureSource(
        "sec-edgar",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        "company filing time series",
    ),
    ApprovedFutureSource(
        "gtfs-realtime",
        "General Transit Feed Specification publishers",
        "https://gtfs.org/documentation/realtime/realtime-best-practices/",
        "public-transport operational time series",
    ),
)


def build_default_adapters(http: HttpClient) -> list[DatasetSourceAdapter]:
    return [
        LocalUploadAdapter(),
        PMDWIS2Adapter(http),
        WorldBankAdapter(http),
        NASAPowerAdapter(http),
        WHOGHOAdapter(http),
        *international_catalog_adapters(http),
        *pakistan_catalog_adapters(http),
        research_catalog_adapter(http),
    ]
