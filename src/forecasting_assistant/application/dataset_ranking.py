from __future__ import annotations

import re
from datetime import UTC, date, datetime

from forecasting_assistant.domain.datasets import (
    AcquisitionMode,
    CatalogClass,
    DatasetCandidate,
    DatasetSearchQuery,
    RankingBreakdown,
    SourceRole,
)

_TOKENS = re.compile(r"[a-z0-9]+")
_PAKISTAN_PRIMARY_PUBLISHERS = {
    "pakistan meteorological department",
    "state bank of pakistan",
    "pakistan bureau of statistics",
    "national disaster management authority",
}


def _tokens(value: str) -> set[str]:
    ignored = {"a", "an", "and", "for", "in", "of", "the", "to"}
    return {token for token in _TOKENS.findall(value.casefold()) if token not in ignored}


def _frequency_unit(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.casefold().strip()
    aliases = {
        "hour": "hourly",
        "day": "daily",
        "week": "weekly",
        "month": "monthly",
        "quarter": "quarterly",
        "year": "annual",
        "yearly": "annual",
    }
    return aliases.get(normalized, normalized)


def _geography_matches(query: DatasetSearchQuery, candidate: DatasetCandidate) -> bool:
    if not query.geography or not candidate.geography:
        return True
    requested = _tokens(" ".join(query.geography))
    available = _tokens(" ".join(candidate.geography))
    if "global" in available or "world" in available:
        return True
    return bool(requested & available)


class DatasetRanker:
    """Fail-closed eligibility and deterministic source ranking."""

    def rank(
        self, candidate: DatasetCandidate, query: DatasetSearchQuery, *, today: date | None = None
    ) -> RankingBreakdown:
        current_date = today or datetime.now(UTC).date()
        rejection_reasons = self._eligibility_reasons(candidate, query)
        limitations = list(candidate.access_restrictions) + list(candidate.quality.warnings)

        semantic = self._semantic_score(candidate, query)
        authority = self._authority_score(candidate, query)
        temporal = self._temporal_score(candidate, query)
        quality = self._quality_score(candidate)
        license_score = self._license_score(candidate, query)
        freshness = self._freshness_score(candidate, current_date)
        access = self._access_score(candidate)

        return RankingBreakdown(
            candidate_id=candidate.candidate_id,
            eligible=not rejection_reasons,
            task_semantic_fit=semantic,
            authority_provenance=authority,
            temporal_fit=temporal,
            quality=quality,
            license_reproducibility=license_score,
            freshness=freshness,
            access_reliability_cost=access,
            rejection_reasons=rejection_reasons,
            limitations=list(dict.fromkeys(limitations)),
        )

    def _eligibility_reasons(
        self, candidate: DatasetCandidate, query: DatasetSearchQuery
    ) -> list[str]:
        reasons: list[str] = []
        license_assessment = candidate.license
        if query.purpose == CatalogClass.PRODUCTION:
            if candidate.catalog_class == CatalogClass.RESEARCH or license_assessment.research_only:
                reasons.append("research-only dataset is not eligible for production")
            if not license_assessment.verified:
                reasons.append("license or reuse rights are not verified")
            if license_assessment.commercial_use_allowed is False:
                reasons.append("license is incompatible with production or value-added use")
            if license_assessment.redistribution_allowed is False and query.user_id is None:
                reasons.append("non-redistributable data requires a user-scoped request")

        if not candidate.publisher.strip() or not candidate.original_publisher_verified:
            reasons.append("original publisher or provenance is not verified")
        if candidate.source_role == SourceRole.AGGREGATOR and not candidate.original_publisher_verified:
            reasons.append("aggregator entry has not been resolved to its original publisher")
        if candidate.acquisition_mode in {
            AcquisitionMode.REQUEST_REQUIRED,
            AcquisitionMode.DISCOVERY_ONLY,
        }:
            reasons.append("source requires manual access or discovery resolution")
        if query.contains_sensitive_data and not query.user_id:
            reasons.append("sensitive data requires an authenticated user scope")
        if not _geography_matches(query, candidate):
            reasons.append("geography does not match the forecasting specification")
        requested_frequency = _frequency_unit(query.frequency)
        available_frequency = _frequency_unit(candidate.frequency)
        if requested_frequency and available_frequency and requested_frequency != available_frequency:
            reasons.append("observation frequency does not match the forecasting specification")
        if (
            candidate.quality.training_points is not None
            and candidate.quality.training_points < query.minimum_training_points
        ):
            reasons.append("dataset has fewer than the minimum required training points")
        if (
            query.maximum_staleness_days is not None
            and candidate.quality.staleness_days is not None
            and candidate.quality.staleness_days > query.maximum_staleness_days
        ):
            reasons.append("dataset exceeds the maximum permitted staleness")
        if candidate.quality.integrity_valid is False:
            reasons.append("dataset integrity validation failed")
        if candidate.quality.schema_valid is False:
            reasons.append("dataset schema validation failed")
        if candidate.quality.timestamp_valid is False:
            reasons.append("dataset timestamps are invalid")
        return list(dict.fromkeys(reasons))

    def _semantic_score(self, candidate: DatasetCandidate, query: DatasetSearchQuery) -> float:
        requested = _tokens(query.target)
        candidate_tokens = _tokens(
            " ".join(
                [candidate.title, candidate.description, *candidate.target_variables, *candidate.tags]
            )
        )
        if not requested:
            base = 8.0
        else:
            overlap = len(requested & candidate_tokens) / len(requested)
            base = 6.0 + 17.0 * overlap
        if _geography_matches(query, candidate) and query.geography:
            base += 4.0
        if query.is_pakistan and "pakistan" in _tokens(" ".join(candidate.geography)):
            base += 3.0
        return round(min(30.0, base), 2)

    def _authority_score(self, candidate: DatasetCandidate, query: DatasetSearchQuery) -> float:
        role_scores = {
            SourceRole.PRIMARY: 18.0,
            SourceRole.OFFICIAL_SECONDARY: 15.0,
            SourceRole.REQUEST_BASED: 14.0,
            SourceRole.RESEARCH: 8.0,
            SourceRole.AGGREGATOR: 3.0,
        }
        score = role_scores[candidate.source_role]
        if candidate.official and candidate.original_publisher_verified:
            score += 2.0
        if query.is_pakistan and candidate.publisher.casefold() in _PAKISTAN_PRIMARY_PUBLISHERS:
            score += 1.0
        return min(20.0, score)

    def _temporal_score(self, candidate: DatasetCandidate, query: DatasetSearchQuery) -> float:
        score = 5.0
        if candidate.frequency:
            score += 3.0 if _frequency_unit(candidate.frequency) == _frequency_unit(query.frequency) else 0
        if candidate.temporal_start:
            score += 2.0
            if query.history_start and candidate.temporal_start <= query.history_start:
                score += 2.0
        if candidate.temporal_end:
            score += 1.0
            if query.history_end and candidate.temporal_end >= query.history_end:
                score += 2.0
        return min(15.0, score)

    def _quality_score(self, candidate: DatasetCandidate) -> float:
        report = candidate.quality
        score = 6.0
        if report.integrity_valid is True:
            score += 2.0
        if report.schema_valid is True:
            score += 2.0
        if report.timestamp_valid is True:
            score += 2.0
        if report.missing_ratio is not None:
            score += max(0.0, 2.0 * (1.0 - report.missing_ratio))
        if report.human_verified:
            score += 1.0
        return round(min(15.0, score), 2)

    def _license_score(self, candidate: DatasetCandidate, query: DatasetSearchQuery) -> float:
        license_assessment = candidate.license
        if not license_assessment.verified:
            return 0.0
        if license_assessment.research_only and query.purpose == CatalogClass.PRODUCTION:
            return 1.0
        score = 5.0
        if license_assessment.commercial_use_allowed is True:
            score += 2.0
        if license_assessment.redistribution_allowed is True:
            score += 3.0
        return min(10.0, score)

    def _freshness_score(self, candidate: DatasetCandidate, today: date) -> float:
        reference = candidate.release_date or candidate.temporal_end
        if reference is None:
            return 1.0
        age = max(0, (today - reference).days)
        if age <= 31:
            return 5.0
        if age <= 366:
            return 4.0
        if age <= 3 * 366:
            return 2.5
        return 1.0

    def _access_score(self, candidate: DatasetCandidate) -> float:
        if candidate.acquisition_mode == AcquisitionMode.API and candidate.stable_machine_interface:
            score = 5.0
        elif candidate.acquisition_mode == AcquisitionMode.DOWNLOAD:
            score = 3.5
        elif candidate.acquisition_mode == AcquisitionMode.LOCAL_UPLOAD:
            score = 3.0
        elif candidate.acquisition_mode == AcquisitionMode.PUBLICATION:
            score = 1.5
        else:
            score = 0.5
        if candidate.cost and candidate.cost.casefold() not in {"free", "none"}:
            score = max(0.0, score - 1.5)
        if candidate.credential_reference:
            score = max(0.0, score - 0.5)
        return score


def ranking_sort_key(item: tuple[DatasetCandidate, RankingBreakdown]) -> tuple[object, ...]:
    candidate, ranking = item
    role_order = {
        SourceRole.PRIMARY: 0,
        SourceRole.OFFICIAL_SECONDARY: 1,
        SourceRole.REQUEST_BASED: 2,
        SourceRole.RESEARCH: 3,
        SourceRole.AGGREGATOR: 4,
    }
    return (
        -ranking.total,
        role_order[candidate.source_role],
        -(candidate.release_date.toordinal() if candidate.release_date else 0),
        -(candidate.temporal_start.toordinal() if candidate.temporal_start else 0),
        0 if candidate.stable_machine_interface else 1,
        candidate.candidate_id,
    )
