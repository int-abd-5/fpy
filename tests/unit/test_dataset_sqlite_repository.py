from pathlib import Path
from uuid import uuid4

from forecasting_assistant.domain.datasets import (
    AcquisitionMode,
    CatalogClass,
    DatasetCandidate,
    DatasetSearchQuery,
    DatasetSelection,
    DatasetVersion,
    LicenseAssessment,
    SourcePlan,
    SourceRole,
)
from forecasting_assistant.infrastructure.datasets.sqlite_repository import (
    SQLiteDatasetCatalogRepository,
)


def test_dataset_catalog_round_trips_candidate_plan_selection_and_version(tmp_path: Path) -> None:
    repository = SQLiteDatasetCatalogRepository(tmp_path / "catalog.db")
    repository.initialize()
    candidate = DatasetCandidate(
        candidate_id="candidate-1",
        adapter_id="official",
        canonical_identifier="series-1",
        title="Official series",
        publisher="Official publisher",
        source_url="https://example.com/data.csv",
        catalog_class=CatalogClass.PRODUCTION,
        source_role=SourceRole.PRIMARY,
        acquisition_mode=AcquisitionMode.DOWNLOAD,
        official=True,
        original_publisher_verified=True,
        license=LicenseAssessment(
            name="open",
            verified=True,
            commercial_use_allowed=True,
            redistribution_allowed=True,
        ),
    )
    repository.save_candidate(candidate)
    plan = SourcePlan(
        specification_id=uuid4(),
        query=DatasetSearchQuery(target="series"),
    )
    repository.save_plan(plan)
    selection = DatasetSelection(
        plan_id=plan.plan_id,
        specification_id=plan.specification_id,
        candidate_id=candidate.candidate_id,
    )
    repository.save_selection(selection)
    version = DatasetVersion(
        candidate_id=candidate.candidate_id,
        cache_key="cache-1",
        sha256="0" * 64,
        storage_path="objects/00/value",
        byte_size=10,
        shared=True,
        license_snapshot=candidate.license,
    )
    repository.save_version(version)

    assert repository.load_candidate(candidate.candidate_id) == candidate
    assert repository.load_plan(plan.plan_id) == plan
    assert repository.load_selection(selection.selection_id) == selection
    assert repository.load_version(version.version_id) == version
    assert repository.find_cached_version("cache-1", user_id=None) == version
