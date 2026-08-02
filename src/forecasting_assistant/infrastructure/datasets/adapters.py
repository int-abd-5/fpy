from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlencode

from forecasting_assistant.domain.datasets import (
    AcquisitionMode,
    CatalogClass,
    DatasetCandidate,
    DatasetSearchQuery,
    FetchResult,
    LicenseAssessment,
    SourceRole,
)
from forecasting_assistant.infrastructure.datasets.http import DatasetDownloadError
from forecasting_assistant.infrastructure.datasets.protocol import HttpClient

_WORDS = re.compile(r"[a-z0-9]+")


def _words(value: str) -> set[str]:
    return set(_WORDS.findall(value.casefold()))


def _matches(query: DatasetSearchQuery, candidate: DatasetCandidate) -> bool:
    requested = _words(query.target)
    available = _words(
        " ".join(
            [candidate.title, candidate.description, *candidate.target_variables, *candidate.tags]
        )
    )
    if requested and not requested & available:
        return False
    if query.geography and candidate.geography:
        requested_geo = _words(" ".join(query.geography))
        candidate_geo = _words(" ".join(candidate.geography))
        if not requested_geo & candidate_geo and not candidate_geo & {"global", "world"}:
            return False
    return True


def _candidate(
    adapter_id: str,
    identifier: str,
    *,
    title: str,
    publisher: str,
    source_url: str,
    catalog_class: CatalogClass = CatalogClass.PRODUCTION,
    source_role: SourceRole = SourceRole.PRIMARY,
    acquisition_mode: AcquisitionMode = AcquisitionMode.PUBLICATION,
    description: str = "",
    official: bool = True,
    provenance: bool = True,
    geography: list[str] | None = None,
    targets: list[str] | None = None,
    tags: list[str] | None = None,
    frequency: str | None = None,
    unit: str | None = None,
    license_assessment: LicenseAssessment | None = None,
    stable: bool = False,
    cost: str | None = "free",
    access_restrictions: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DatasetCandidate:
    return DatasetCandidate(
        candidate_id=DatasetCandidate.stable_id(adapter_id, identifier),
        adapter_id=adapter_id,
        canonical_identifier=identifier,
        title=title,
        description=description,
        publisher=publisher,
        source_url=source_url,
        catalog_class=catalog_class,
        source_role=source_role,
        acquisition_mode=acquisition_mode,
        official=official,
        original_publisher_verified=provenance,
        geography=geography or [],
        target_variables=targets or [],
        tags=tags or [],
        frequency=frequency,
        unit=unit,
        license=license_assessment or LicenseAssessment(),
        stable_machine_interface=stable,
        cost=cost,
        access_restrictions=access_restrictions or [],
        metadata=metadata or {},
        query_identity=(
            source_url
            if acquisition_mode in {AcquisitionMode.API, AcquisitionMode.DOWNLOAD}
            else None
        ),
    )


OPEN_PUBLIC_LICENSE = LicenseAssessment(
    name="official open data terms",
    verified=True,
    commercial_use_allowed=True,
    redistribution_allowed=True,
)
OFFICIAL_USE_REVIEW = LicenseAssessment(
    name="official public statistical release; dataset-specific reuse review required",
    verified=True,
    commercial_use_allowed=None,
    redistribution_allowed=None,
    restrictions=["shared caching requires a dataset-specific redistribution assessment"],
)
UNKNOWN_PUBLICATION_RIGHTS = LicenseAssessment(
    name="official publication; reuse rights not established",
    verified=False,
    restrictions=["metadata only until reuse terms are verified"],
)
RESEARCH_LICENSE = LicenseAssessment(
    name="research use only or underlying rights require review",
    verified=True,
    commercial_use_allowed=False,
    redistribution_allowed=False,
    research_only=True,
)


class StaticCatalogAdapter:
    def __init__(
        self,
        source_id: str,
        candidates: list[DatasetCandidate],
        http: HttpClient,
    ) -> None:
        self.source_id = source_id
        self._candidates = {candidate.candidate_id: candidate for candidate in candidates}
        self._http = http

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        return [candidate.model_copy(deep=True) for candidate in self._candidates.values() if _matches(query, candidate)]

    def describe(self, candidate_id: str) -> DatasetCandidate:
        try:
            return self._candidates[candidate_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError(f"unknown {self.source_id} dataset candidate") from error

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        fetch_url = candidate.metadata.get("fetch_url")
        if not isinstance(fetch_url, str):
            if candidate.acquisition_mode in {
                AcquisitionMode.PUBLICATION,
                AcquisitionMode.DISCOVERY_ONLY,
                AcquisitionMode.REQUEST_REQUIRED,
            }:
                raise DatasetDownloadError("source is metadata-only or requires manual access")
            fetch_url = candidate.source_url
        return self._http.get_bytes(fetch_url)


class LocalUploadAdapter:
    source_id = "local-upload"

    def __init__(self) -> None:
        self._candidates: dict[str, DatasetCandidate] = {}

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        if query.source_mode != "upload" or not query.source_reference:
            return []
        source = Path(query.source_reference).expanduser()
        identifier = str(source.resolve(strict=False))
        license_assessment = LicenseAssessment(
            name=query.license_hint or "user-provided private data",
            verified=True,
            commercial_use_allowed=True,
            redistribution_allowed=False,
            restrictions=["user-scoped; uploader is responsible for authorization"],
        )
        result = _candidate(
            self.source_id,
            identifier,
            title=source.name,
            publisher="User-provided source",
            source_url=source.as_uri() if source.is_absolute() else str(source),
            source_role=SourceRole.PRIMARY,
            acquisition_mode=AcquisitionMode.LOCAL_UPLOAD,
            description="Local dataset supplied for this forecasting specification.",
            official=False,
            provenance=True,
            targets=[query.target],
            geography=query.geography,
            frequency=query.frequency,
            license_assessment=license_assessment,
            access_restrictions=["private user-scoped data"],
            metadata={"local_path": identifier},
        )
        self._candidates[result.candidate_id] = result
        return [result.model_copy(deep=True)]

    def describe(self, candidate_id: str) -> DatasetCandidate:
        return self._candidates[candidate_id].model_copy(deep=True)

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        raw_path = candidate.metadata.get("local_path")
        if not isinstance(raw_path, str):
            raise DatasetDownloadError("local dataset path is missing")
        path = Path(raw_path)
        if not path.is_file():
            raise DatasetDownloadError("local dataset does not exist")
        if path.suffix.casefold() in {".bat", ".cmd", ".exe", ".msi", ".ps1", ".sh"}:
            raise DatasetDownloadError("executable local uploads are prohibited")
        return FetchResult(content=path.read_bytes(), metadata={"filename": path.name})


class PMDWIS2Adapter:
    source_id = "pmd-wis2"
    _discovery_url = (
        "https://wis2box.pmd.gov.pk/oapi/collections/discovery-metadata/items?f=json&limit=100"
    )

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._candidates: dict[str, DatasetCandidate] = {}

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        if not query.is_pakistan:
            return []
        payload = self._http.get_json(self._discovery_url)
        features = payload.get("features", []) if isinstance(payload, dict) else []
        results: list[DatasetCandidate] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties", {})
            if not isinstance(properties, dict):
                continue
            identifier = str(
                properties.get("identifier") or feature.get("id") or properties.get("title") or ""
            ).strip()
            if not identifier:
                continue
            title = str(properties.get("title") or identifier)
            description = str(properties.get("description") or properties.get("abstract") or "")
            policy = str(
                properties.get("wmo:dataPolicy")
                or properties.get("wmo_data_policy")
                or properties.get("dataPolicy")
                or ""
            ).casefold()
            links = feature.get("links", [])
            data_url = self._discovery_url
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, dict) and link.get("href") and link.get("rel") in {
                        "canonical",
                        "data",
                        "items",
                    }:
                        data_url = str(link["href"])
                        break
            license_assessment = LicenseAssessment(
                name="WMO Unified Data Policy - core" if "core" in policy else None,
                url="https://public.wmo.int/wmo-unified-data-policy-resolution-res1",
                verified="core" in policy,
                commercial_use_allowed=True if "core" in policy else None,
                redistribution_allowed=True if "core" in policy else None,
                restrictions=[] if "core" in policy else ["WMO data-policy classification requires review"],
            )
            frequency = None
            lowered = f"{title} {description}".casefold()
            if "daily" in lowered:
                frequency = "daily"
            elif "three-hour" in lowered or "3-hour" in lowered:
                frequency = "every 3 hour"
            candidate = _candidate(
                self.source_id,
                identifier,
                title=title,
                description=description,
                publisher="Pakistan Meteorological Department",
                source_url=data_url,
                source_role=SourceRole.PRIMARY,
                acquisition_mode=AcquisitionMode.API,
                geography=["Pakistan"],
                targets=["weather", "temperature", "rainfall", "climate", "alerts"],
                tags=["station observations", "synoptic", "marine", "CAP"],
                frequency=frequency,
                license_assessment=license_assessment,
                stable=True,
                metadata={"wmo_data_policy": policy, "discovery_url": self._discovery_url},
            )
            if _matches(query, candidate):
                self._candidates[candidate.candidate_id] = candidate
                results.append(candidate)
        return results

    def describe(self, candidate_id: str) -> DatasetCandidate:
        return self._candidates[candidate_id].model_copy(deep=True)

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        return self._http.get_bytes(candidate.source_url)


class WorldBankAdapter:
    source_id = "world-bank"
    _indicators: ClassVar[dict[str, tuple[str, list[str], str]]] = {
        "SP.POP.TOTL": ("Population, total", ["population", "demography"], "people"),
        "NY.GDP.MKTP.CD": ("GDP (current US$)", ["gdp", "economy"], "USD"),
        "FP.CPI.TOTL": ("Consumer price index", ["cpi", "prices", "inflation"], "index"),
        "FP.CPI.TOTL.ZG": ("Inflation, consumer prices", ["inflation", "cpi"], "percent"),
        "BX.TRF.PWKR.CD.DT": ("Personal remittances, received", ["remittances"], "USD"),
    }
    _country_codes: ClassVar[dict[str, str]] = {
        "pakistan": "PK",
        "global": "all",
        "world": "all",
    }

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._candidates: dict[str, DatasetCandidate] = {}

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        geography = query.geography[0] if query.geography else "global"
        country = self._country_codes.get(geography.casefold(), "all")
        results: list[DatasetCandidate] = []
        for indicator, (title, tags, unit) in self._indicators.items():
            params = urlencode({"format": "json", "per_page": 20000})
            url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?{params}"
            candidate = _candidate(
                self.source_id,
                f"{country}:{indicator}",
                title=title,
                description="World Development Indicators time series.",
                publisher="World Bank",
                source_url=url,
                source_role=SourceRole.OFFICIAL_SECONDARY,
                acquisition_mode=AcquisitionMode.API,
                geography=[geography, "global"],
                targets=[title],
                tags=tags,
                frequency="annual",
                unit=unit,
                license_assessment=LicenseAssessment(
                    name="CC BY 4.0",
                    url="https://datacatalog.worldbank.org/public-licenses",
                    verified=True,
                    commercial_use_allowed=True,
                    redistribution_allowed=True,
                ),
                stable=True,
                metadata={"unit": unit, "indicator": indicator, "country": country},
            )
            if _matches(query, candidate):
                self._candidates[candidate.candidate_id] = candidate
                results.append(candidate)
        return results

    def describe(self, candidate_id: str) -> DatasetCandidate:
        return self._candidates[candidate_id].model_copy(deep=True)

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        return self._http.get_bytes(candidate.source_url)


class NASAPowerAdapter:
    source_id = "nasa-power"

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._candidates: dict[str, DatasetCandidate] = {}

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        weather_terms = _words("temperature rainfall precipitation solar wind weather climate")
        if not _words(query.target) & weather_terms or query.latitude is None or query.longitude is None:
            return []
        parameter = "PRECTOTCORR" if _words(query.target) & {"rainfall", "precipitation"} else "T2M"
        start = (query.history_start or date(1981, 1, 1)).strftime("%Y%m%d")
        end = (query.history_end or datetime.now(UTC).date()).strftime("%Y%m%d")
        params = urlencode(
            {
                "parameters": parameter,
                "community": "AG",
                "longitude": query.longitude,
                "latitude": query.latitude,
                "start": start,
                "end": end,
                "format": "JSON",
            }
        )
        url = f"https://power.larc.nasa.gov/api/temporal/daily/point?{params}"
        identifier = f"{parameter}:{query.latitude}:{query.longitude}:{start}:{end}"
        candidate = _candidate(
            self.source_id,
            identifier,
            title=f"NASA POWER daily {parameter}",
            description="Modeled gridded meteorological time series for a geographic point.",
            publisher="NASA POWER",
            source_url=url,
            source_role=SourceRole.OFFICIAL_SECONDARY,
            acquisition_mode=AcquisitionMode.API,
            geography=query.geography or ["global"],
            targets=["temperature", "rainfall", "weather", "climate"],
            tags=["modeled", "gridded", parameter],
            frequency="daily",
            license_assessment=OPEN_PUBLIC_LICENSE,
            stable=True,
            metadata={"parameter": parameter, "modeled": True},
        )
        self._candidates[candidate.candidate_id] = candidate
        return [candidate]

    def describe(self, candidate_id: str) -> DatasetCandidate:
        return self._candidates[candidate_id].model_copy(deep=True)

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        return self._http.get_bytes(candidate.source_url)


class WHOGHOAdapter:
    source_id = "who-gho"
    _indicator_url = "https://ghoapi.azureedge.net/api/Indicator"

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._candidates: dict[str, DatasetCandidate] = {}

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        health_terms = _words("health disease mortality morbidity life expectancy vaccination")
        if not _words(query.target) & health_terms:
            return []
        payload = self._http.get_json(self._indicator_url)
        records = payload.get("value", []) if isinstance(payload, dict) else []
        results: list[DatasetCandidate] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            code = str(record.get("IndicatorCode") or "").strip()
            title = str(record.get("IndicatorName") or "").strip()
            if not code or not title or not _words(query.target) & _words(title):
                continue
            data_url = f"https://ghoapi.azureedge.net/api/{code}"
            if query.is_pakistan:
                data_url += "?$filter=SpatialDim%20eq%20%27PAK%27"
            candidate = _candidate(
                self.source_id,
                code,
                title=title,
                description="WHO Global Health Observatory indicator time series.",
                publisher="World Health Organization",
                source_url=data_url,
                source_role=SourceRole.OFFICIAL_SECONDARY,
                acquisition_mode=AcquisitionMode.API,
                geography=query.geography or ["global"],
                targets=[title, "health"],
                tags=[code, "Global Health Observatory"],
                license_assessment=LicenseAssessment(
                    name="WHO data terms",
                    url="https://www.who.int/about/policies/publishing/copyright",
                    verified=True,
                    commercial_use_allowed=None,
                    redistribution_allowed=None,
                    restrictions=["indicator-specific attribution and reuse terms must be retained"],
                ),
                stable=True,
                access_restrictions=["shared caching requires indicator-specific rights verification"],
            )
            self._candidates[candidate.candidate_id] = candidate
            results.append(candidate)
            if len(results) == 10:
                break
        return results

    def describe(self, candidate_id: str) -> DatasetCandidate:
        return self._candidates[candidate_id].model_copy(deep=True)

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        return self._http.get_bytes(candidate.source_url)


def pakistan_catalog_adapters(http: HttpClient) -> list[StaticCatalogAdapter]:
    pmd_cdpc = _candidate(
        "pmd-cdpc",
        "historic-climate-request",
        title="PMD historical climate observations",
        description="Hourly, daily, or monthly temperature, rainfall, humidity, wind and pressure.",
        publisher="Pakistan Meteorological Department",
        source_url="https://www.pmd.gov.pk/rmc/RMCK/Services_Climatology.html",
        source_role=SourceRole.REQUEST_BASED,
        acquisition_mode=AcquisitionMode.REQUEST_REQUIRED,
        geography=["Pakistan"],
        targets=["weather", "temperature", "rainfall", "humidity", "wind", "pressure"],
        license_assessment=LicenseAssessment(
            name="PMD supplied-data terms",
            url="https://cdpc.pmd.gov.pk/cost.htm",
            verified=True,
            commercial_use_allowed=False,
            redistribution_allowed=False,
            restrictions=["may not be passed to third parties or used for value-added services"],
        ),
        cost="request-based or paid",
    )
    ndma = [
        _candidate(
            "ndma",
            identifier,
            title=title,
            description="Official Pakistan disaster-risk publication catalog.",
            publisher="National Disaster Management Authority",
            source_url=url,
            source_role=role,
            acquisition_mode=mode,
            geography=["Pakistan"],
            targets=["disaster", "flood", "hazard", "impact", "risk", "damage"],
            tags=["advisory", "situation report", "projection", "MHVRA"],
            license_assessment=UNKNOWN_PUBLICATION_RIGHTS,
        )
        for identifier, title, url, role, mode in [
            ("early-warning", "NDMA early warnings and projections", "https://www.ndma.gov.pk/ew", SourceRole.PRIMARY, AcquisitionMode.PUBLICATION),
            ("library", "NDMA e-library", "https://library.ndma.gov.pk/library", SourceRole.PRIMARY, AcquisitionMode.PUBLICATION),
            ("sitreps", "NDMA situation reports", "https://ndma.gov.pk/sitreps?cat_id=1", SourceRole.PRIMARY, AcquisitionMode.PUBLICATION),
            ("e-mhvra", "NDMA e-MHVRA risk data", "https://www.ndma.gov.pk/public/publication_by_category/14", SourceRole.REQUEST_BASED, AcquisitionMode.REQUEST_REQUIRED),
        ]
    ]
    sbp = [
        _candidate(
            "sbp",
            identifier,
            title=title,
            description="Official Pakistani monetary, banking, exchange-rate, trade and remittance series.",
            publisher="State Bank of Pakistan",
            source_url=url,
            source_role=SourceRole.PRIMARY,
            acquisition_mode=AcquisitionMode.DISCOVERY_ONLY,
            geography=["Pakistan"],
            targets=["policy rate", "exchange rate", "money", "banking", "trade", "remittances", "inflation"],
            tags=["macroeconomic", "financial"],
            license_assessment=OFFICIAL_USE_REVIEW,
            access_restrictions=["shared caching requires dataset-specific rights verification"],
        )
        for identifier, title, url in [
            ("easydata", "SBP EasyData time-series catalog", "https://easydata.sbp.org.pk/apex/f?p=10:1:0:"),
            ("ecodata", "SBP economic data archive", "https://archive.sbp.org.pk/ecodata/index2.asp"),
        ]
    ]
    pbs = _candidate(
        "pbs",
        "pds",
        title="PBS official time-series data",
        description="Official CPI, census, labour, trade and agriculture statistics.",
        publisher="Pakistan Bureau of Statistics",
        source_url="https://www.pbs.gov.pk/pds/",
        source_role=SourceRole.PRIMARY,
        acquisition_mode=AcquisitionMode.DISCOVERY_ONLY,
        geography=["Pakistan"],
        targets=["cpi", "census", "population", "labour", "trade", "agriculture", "inflation"],
        tags=["official statistics", "aggregate tables"],
        license_assessment=OFFICIAL_USE_REVIEW,
        access_restrictions=["microdata and charged surveys remain restricted"],
    )
    publication_rows = [
        ("ffd", "flood-dashboard", "PMD Flood Forecasting Division", "Pakistan Meteorological Department", "https://ffd.pmd.gov.pk/home", ["flood", "river flow", "forecast"]),
        ("finance-pk", "economic-survey", "Pakistan Economic Survey", "Ministry of Finance Pakistan", "https://www.finance.gov.pk/survey_2025.html", ["economy", "agriculture", "health", "education", "energy"]),
        ("ffc", "annual-reports", "Federal Flood Commission annual reports", "Federal Flood Commission", "https://ffc.gov.pk/", ["flood", "hydrology", "damage"]),
        ("nepra", "annual-reports", "NEPRA annual and State of Industry reports", "National Electric Power Regulatory Authority", "https://nepra.org.pk/publications/Annual%20Reports.php", ["electricity", "power", "generation", "capacity"]),
        ("power-division", "reports", "Power Division monthly reports", "Ministry of Energy Pakistan", "https://power.gov.pk/Reports", ["electricity", "power", "generation", "distribution"]),
        ("wapda", "reports", "WAPDA hydrological and energy reports", "Water and Power Development Authority", "https://wapda.gov.pk/", ["hydrology", "water", "electricity", "power"]),
        ("suparco", "disaster-watch", "SUPARCO disaster management products", "SUPARCO", "https://www.suparco.gov.pk/products-services/disaster-management/", ["satellite", "disaster", "flood", "hazard"]),
        ("pcrwr", "water-quality", "PCRWR water-quality reports", "Pakistan Council of Research in Water Resources", "https://www.pcrwr.gov.pk/water-quality-reports/", ["water quality", "water", "contamination"]),
        ("pdma-kp", "sitreps", "KP PDMA situation reports and damages", "Provincial Disaster Management Authority Khyber Pakhtunkhwa", "https://www.pdma.gov.pk/", ["disaster", "flood", "damage", "khyber pakhtunkhwa"]),
        ("pdma-sindh", "sitreps", "Sindh PDMA situation reports", "Provincial Disaster Management Authority Sindh", "https://pdma.gos.pk/", ["disaster", "flood", "damage", "sindh"]),
        ("pdma-punjab", "sitreps", "Punjab PDMA situation reports", "Provincial Disaster Management Authority Punjab", "https://pdma.gop.pk/", ["disaster", "flood", "damage", "punjab"]),
    ]
    publications = [
        _candidate(
            adapter,
            identifier,
            title=title,
            description="Official Pakistan publication source; table extraction requires a versioned template and human verification.",
            publisher=publisher,
            source_url=url,
            source_role=SourceRole.PRIMARY,
            acquisition_mode=AcquisitionMode.PUBLICATION,
            geography=["Pakistan", *([tags[-1]] if tags[-1] in {"sindh", "punjab", "khyber pakhtunkhwa"} else [])],
            targets=tags,
            tags=["official publication", "manual QA required"],
            license_assessment=UNKNOWN_PUBLICATION_RIGHTS,
            access_restrictions=["PDF or dashboard data is not production-approved without extraction QA"],
        )
        for adapter, identifier, title, publisher, url, tags in publication_rows
    ]
    aggregator = _candidate(
        "open-data-pakistan",
        "catalog",
        title="Open Data Pakistan discovery catalog",
        description="Secondary discovery catalog; every result must resolve to an original official publisher.",
        publisher="Open Data Pakistan",
        source_url="https://opendata.com.pk/",
        source_role=SourceRole.AGGREGATOR,
        acquisition_mode=AcquisitionMode.DISCOVERY_ONLY,
        official=False,
        provenance=False,
        geography=["Pakistan"],
        targets=["statistics", "economy", "population", "government"],
        license_assessment=UNKNOWN_PUBLICATION_RIGHTS,
    )
    grouped: dict[str, list[DatasetCandidate]] = {
        "pmd-cdpc": [pmd_cdpc],
        "ndma": ndma,
        "sbp": sbp,
        "pbs": [pbs],
        "open-data-pakistan": [aggregator],
    }
    adapters = [
        StaticCatalogAdapter(source_id, candidates, http)
        for source_id, candidates in grouped.items()
    ]
    adapters.extend(
        StaticCatalogAdapter(candidate.adapter_id, [candidate], http)
        for candidate in publications
    )
    return adapters


def international_catalog_adapters(http: HttpClient) -> list[StaticCatalogAdapter]:
    rows = [
        ("noaa-ncei", "daily-summaries", "NOAA NCEI Daily Summaries", "NOAA National Centers for Environmental Information", "https://www.ncei.noaa.gov/index.php/support/access-data-service-api-user-documentation", ["weather", "temperature", "precipitation", "climate"], "daily", OPEN_PUBLIC_LICENSE, "API token and station selection must be resolved before creating a fetchable candidate"),
        ("fred", "series-api", "FRED economic time series", "Federal Reserve Bank of St. Louis", "https://fred.stlouisfed.org/docs/api/fred/", ["economy", "interest rate", "inflation", "exchange rate", "financial"], None, OPEN_PUBLIC_LICENSE, "API credentials must be resolved outside persisted metadata"),
        ("eia", "open-data", "EIA energy time series", "U.S. Energy Information Administration", "https://www.eia.gov/opendata/documentation.php", ["energy", "electricity", "oil", "gas", "generation"], None, OPEN_PUBLIC_LICENSE, "API credentials and a concrete route must be resolved before selection"),
    ]
    results: list[StaticCatalogAdapter] = []
    for adapter, identifier, title, publisher, url, targets, frequency, license_assessment, restriction in rows:
        candidate = _candidate(
            adapter,
            identifier,
            title=title,
            description="Official machine-readable international dataset service.",
            publisher=publisher,
            source_url=url,
            source_role=SourceRole.OFFICIAL_SECONDARY,
            acquisition_mode=AcquisitionMode.DISCOVERY_ONLY,
            geography=["global"],
            targets=targets,
            tags=targets,
            frequency=frequency,
            license_assessment=license_assessment,
            stable=True,
            access_restrictions=[restriction],
            metadata={"catalog_only": True},
        )
        results.append(StaticCatalogAdapter(adapter, [candidate], http))
    return results


def research_catalog_adapter(http: HttpClient) -> StaticCatalogAdapter:
    candidates = [
        _candidate(
            "research-catalog",
            "autoforecast",
            title="AutoForecast benchmark corpus",
            description="Evaluation-Free Time-Series Forecasting Model Selection via Meta-Learning benchmark references.",
            publisher="Adobe Research and Purdue University",
            source_url="https://research.adobe.com/publication/evaluation-free-time-series-forecasting-model-selection-via-meta-learning/",
            catalog_class=CatalogClass.RESEARCH,
            source_role=SourceRole.RESEARCH,
            acquisition_mode=AcquisitionMode.DISCOVERY_ONLY,
            geography=["global"],
            targets=["time series", "resource usage", "forecasting benchmark"],
            tags=["meta-learning", "benchmark"],
            license_assessment=RESEARCH_LICENSE,
        ),
        _candidate(
            "research-catalog",
            "monash",
            title="Monash Time Series Forecasting Archive",
            description="Forecasting benchmark archive; underlying dataset rights require individual review.",
            publisher="Monash University",
            source_url="https://forecastingdata.org/",
            catalog_class=CatalogClass.RESEARCH,
            source_role=SourceRole.RESEARCH,
            acquisition_mode=AcquisitionMode.DISCOVERY_ONLY,
            geography=["global"],
            targets=["time series", "forecasting benchmark"],
            tags=["benchmark", "archive"],
            license_assessment=RESEARCH_LICENSE,
        ),
    ]
    return StaticCatalogAdapter("research-catalog", candidates, http)
