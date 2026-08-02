from datetime import date

from forecasting_assistant.application.dataset_ranking import DatasetRanker
from forecasting_assistant.domain.datasets import (
    AcquisitionMode,
    CatalogClass,
    DatasetCandidate,
    DatasetSearchQuery,
    LicenseAssessment,
    QualityReport,
    SourceRole,
)


def _candidate(
    identifier: str,
    *,
    publisher: str,
    role: SourceRole,
    geography: list[str],
    targets: list[str],
    frequency: str = "daily",
    catalog_class: CatalogClass = CatalogClass.PRODUCTION,
    license_assessment: LicenseAssessment | None = None,
    provenance: bool = True,
) -> DatasetCandidate:
    return DatasetCandidate(
        candidate_id=DatasetCandidate.stable_id("test", identifier),
        adapter_id="test",
        canonical_identifier=identifier,
        title=identifier,
        publisher=publisher,
        source_url=f"https://example.com/{identifier}",
        catalog_class=catalog_class,
        source_role=role,
        acquisition_mode=AcquisitionMode.API,
        official=True,
        original_publisher_verified=provenance,
        geography=geography,
        target_variables=targets,
        frequency=frequency,
        temporal_start=date(2000, 1, 1),
        temporal_end=date(2026, 7, 31),
        license=license_assessment
        or LicenseAssessment(
            name="open",
            verified=True,
            commercial_use_allowed=True,
            redistribution_allowed=True,
        ),
        quality=QualityReport(
            missing_ratio=0.01,
            timestamp_valid=True,
            schema_valid=True,
            integrity_valid=True,
            training_points=5000,
        ),
        stable_machine_interface=True,
    )


def test_matching_pmd_station_data_ranks_above_modeled_global_weather() -> None:
    query = DatasetSearchQuery(
        target="daily Lahore temperature",
        geography=["Lahore, Pakistan"],
        frequency="daily",
    )
    pmd = _candidate(
        "PMD Lahore station temperature",
        publisher="Pakistan Meteorological Department",
        role=SourceRole.PRIMARY,
        geography=["Lahore", "Pakistan"],
        targets=["station temperature", "weather"],
    )
    nasa = _candidate(
        "NASA modeled temperature",
        publisher="NASA POWER",
        role=SourceRole.OFFICIAL_SECONDARY,
        geography=["global"],
        targets=["modeled temperature", "weather"],
    )

    ranker = DatasetRanker()

    assert ranker.rank(pmd, query).total > ranker.rank(nasa, query).total


def test_frequency_mismatch_disqualifies_pmd_and_allows_global_fallback() -> None:
    query = DatasetSearchQuery(
        target="temperature",
        geography=["Pakistan"],
        frequency="daily",
    )
    pmd = _candidate(
        "PMD monthly temperature",
        publisher="Pakistan Meteorological Department",
        role=SourceRole.PRIMARY,
        geography=["Pakistan"],
        targets=["temperature"],
        frequency="monthly",
    )
    nasa = _candidate(
        "NASA daily temperature",
        publisher="NASA POWER",
        role=SourceRole.OFFICIAL_SECONDARY,
        geography=["global"],
        targets=["temperature"],
    )

    ranker = DatasetRanker()

    assert not ranker.rank(pmd, query).eligible
    assert ranker.rank(nasa, query).eligible


def test_sbp_and_pbs_primary_sources_outrank_secondary_mirrors() -> None:
    ranker = DatasetRanker()
    sbp_query = DatasetSearchQuery(target="Pakistan policy rate", geography=["Pakistan"])
    sbp = _candidate(
        "SBP policy rate",
        publisher="State Bank of Pakistan",
        role=SourceRole.PRIMARY,
        geography=["Pakistan"],
        targets=["policy rate"],
        frequency="monthly",
    )
    mirror = _candidate(
        "World Bank policy rate mirror",
        publisher="World Bank",
        role=SourceRole.OFFICIAL_SECONDARY,
        geography=["global"],
        targets=["policy rate"],
        frequency="monthly",
    )
    pbs_query = DatasetSearchQuery(target="Pakistan census population", geography=["Pakistan"])
    pbs = _candidate(
        "PBS census population",
        publisher="Pakistan Bureau of Statistics",
        role=SourceRole.PRIMARY,
        geography=["Pakistan"],
        targets=["census", "population"],
        frequency="annual",
    )
    aggregator = _candidate(
        "secondary census catalog",
        publisher="Open Data Pakistan",
        role=SourceRole.AGGREGATOR,
        geography=["Pakistan"],
        targets=["census", "population"],
        frequency="annual",
        provenance=False,
    )

    assert ranker.rank(sbp, sbp_query).total > ranker.rank(mirror, sbp_query).total
    assert ranker.rank(pbs, pbs_query).total > ranker.rank(aggregator, pbs_query).total
    assert not ranker.rank(aggregator, pbs_query).eligible


def test_research_and_request_required_sources_fail_production_gates() -> None:
    query = DatasetSearchQuery(target="resource usage")
    research = _candidate(
        "AutoForecast benchmark",
        publisher="Adobe Research",
        role=SourceRole.RESEARCH,
        geography=["global"],
        targets=["resource usage"],
        catalog_class=CatalogClass.RESEARCH,
        license_assessment=LicenseAssessment(
            name="research",
            verified=True,
            commercial_use_allowed=False,
            redistribution_allowed=False,
            research_only=True,
        ),
    )
    request_required = research.model_copy(
        update={
            "candidate_id": DatasetCandidate.stable_id("test", "mhvra"),
            "canonical_identifier": "mhvra",
            "catalog_class": CatalogClass.PRODUCTION,
            "source_role": SourceRole.REQUEST_BASED,
            "acquisition_mode": AcquisitionMode.REQUEST_REQUIRED,
        }
    )

    assert not DatasetRanker().rank(research, query).eligible
    assert not DatasetRanker().rank(request_required, query).eligible
