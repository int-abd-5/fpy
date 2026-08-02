from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class CatalogClass(StrEnum):
    PRODUCTION = "production"
    RESEARCH = "research"


class SourceRole(StrEnum):
    PRIMARY = "primary"
    OFFICIAL_SECONDARY = "official_secondary"
    AGGREGATOR = "aggregator"
    RESEARCH = "research"
    REQUEST_BASED = "request_based"


class AcquisitionMode(StrEnum):
    API = "api"
    DOWNLOAD = "download"
    PUBLICATION = "publication"
    REQUEST_REQUIRED = "request_required"
    DISCOVERY_ONLY = "discovery_only"
    LOCAL_UPLOAD = "local_upload"


class SelectionStatus(StrEnum):
    CONFIRMED = "confirmed"
    FETCHED = "fetched"


class LicenseAssessment(BaseModel):
    name: str | None = None
    url: str | None = None
    verified: bool = False
    commercial_use_allowed: bool | None = None
    redistribution_allowed: bool | None = None
    research_only: bool = False
    restrictions: list[str] = Field(default_factory=list)

    @property
    def production_compatible(self) -> bool:
        return (
            self.verified
            and not self.research_only
            and self.commercial_use_allowed is not False
            and self.redistribution_allowed is not False
        )


class QualityReport(BaseModel):
    missing_ratio: float | None = Field(default=None, ge=0, le=1)
    timestamp_valid: bool | None = None
    schema_valid: bool | None = None
    integrity_valid: bool | None = None
    training_points: int | None = Field(default=None, ge=0)
    staleness_days: int | None = Field(default=None, ge=0)
    human_verified: bool = False
    warnings: list[str] = Field(default_factory=list)


class DatasetSearchQuery(BaseModel):
    target: str
    geography: list[str] = Field(default_factory=list)
    frequency: str | None = None
    history_start: date | None = None
    history_end: date | None = None
    minimum_training_points: int = Field(default=30, ge=1)
    maximum_staleness_days: int | None = Field(default=None, ge=0)
    purpose: CatalogClass = CatalogClass.PRODUCTION
    source_mode: str | None = None
    source_reference: str | None = None
    license_hint: str | None = None
    contains_sensitive_data: bool = False
    user_id: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @property
    def is_pakistan(self) -> bool:
        values = " ".join(self.geography).casefold()
        return any(value in values for value in ("pakistan", " pk", "islamabad", "lahore", "karachi"))


class DatasetCandidate(BaseModel):
    candidate_id: str
    adapter_id: str
    canonical_identifier: str
    title: str
    description: str = ""
    publisher: str
    source_url: str
    catalog_class: CatalogClass
    source_role: SourceRole
    acquisition_mode: AcquisitionMode
    official: bool = False
    original_publisher_verified: bool = False
    geography: list[str] = Field(default_factory=list)
    target_variables: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    unit: str | None = None
    frequency: str | None = None
    temporal_start: date | None = None
    temporal_end: date | None = None
    release_date: date | None = None
    license: LicenseAssessment = Field(default_factory=LicenseAssessment)
    quality: QualityReport = Field(default_factory=QualityReport)
    access_restrictions: list[str] = Field(default_factory=list)
    cost: str | None = None
    credential_reference: str | None = None
    stable_machine_interface: bool = False
    query_identity: str | None = None
    related_candidate_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_identity(self) -> DatasetCandidate:
        if not self.candidate_id.strip() or not self.canonical_identifier.strip():
            raise ValueError("dataset candidates require stable identifiers")
        return self

    @classmethod
    def stable_id(cls, adapter_id: str, canonical_identifier: str) -> str:
        value = f"{adapter_id}:{canonical_identifier}".encode()
        return hashlib.sha256(value).hexdigest()[:24]


class RankingBreakdown(BaseModel):
    candidate_id: str
    eligible: bool
    task_semantic_fit: float = Field(default=0, ge=0, le=30)
    authority_provenance: float = Field(default=0, ge=0, le=20)
    temporal_fit: float = Field(default=0, ge=0, le=15)
    quality: float = Field(default=0, ge=0, le=15)
    license_reproducibility: float = Field(default=0, ge=0, le=10)
    freshness: float = Field(default=0, ge=0, le=5)
    access_reliability_cost: float = Field(default=0, ge=0, le=5)
    total: float = Field(default=0, ge=0, le=100)
    rejection_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def calculate_total(self) -> RankingBreakdown:
        self.total = round(
            self.task_semantic_fit
            + self.authority_provenance
            + self.temporal_fit
            + self.quality
            + self.license_reproducibility
            + self.freshness
            + self.access_reliability_cost,
            2,
        )
        return self


class RankedDatasetCandidate(BaseModel):
    candidate: DatasetCandidate
    ranking: RankingBreakdown


class SourcePlan(BaseModel):
    plan_id: UUID = Field(default_factory=uuid4)
    specification_id: UUID
    query: DatasetSearchQuery
    recommendations: list[RankedDatasetCandidate] = Field(default_factory=list, max_length=3)
    unavailable_alternatives: list[RankedDatasetCandidate] = Field(default_factory=list)
    source_errors: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetSelection(BaseModel):
    selection_id: UUID = Field(default_factory=uuid4)
    plan_id: UUID
    specification_id: UUID
    candidate_id: str
    user_id: str | None = None
    status: SelectionStatus = SelectionStatus.CONFIRMED
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetVersion(BaseModel):
    version_id: UUID = Field(default_factory=uuid4)
    candidate_id: str
    cache_key: str
    sha256: str
    storage_path: str
    byte_size: int = Field(ge=0)
    content_type: str | None = None
    source_version: str | None = None
    query_identity: str | None = None
    shared: bool = False
    user_id: str | None = None
    parent_version_id: UUID | None = None
    license_snapshot: LicenseAssessment
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def cache_identity(
        cls,
        candidate: DatasetCandidate,
        *,
        user_id: str | None,
    ) -> str:
        payload = {
            "adapter": candidate.adapter_id,
            "identifier": candidate.canonical_identifier,
            "query": candidate.query_identity,
            "user": None if candidate.license.redistribution_allowed is True else user_id,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class FetchResult(BaseModel):
    content: bytes
    content_type: str | None = None
    source_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
