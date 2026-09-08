from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from forecasting_assistant.application.interview_ontology import (
    gate_pruned_slots,
    ontology_path,
    relevance_bonus,
)
from forecasting_assistant.application.validation import validate_dialogue
from forecasting_assistant.domain.conditions import is_slot_active
from forecasting_assistant.domain.models import (
    DialogueState,
    Intent,
    ReadinessReport,
    Requiredness,
    SlotStatus,
    ValidationIssue,
)
from forecasting_assistant.domain.schema import ForecastingSchema, SlotDefinition

STATUS_WEIGHTS = {
    SlotStatus.CONFLICTING: 500,
    SlotStatus.INVALID: 450,
    SlotStatus.UNMENTIONED: 400,
    SlotStatus.AMBIGUOUS: 350,
    SlotStatus.INFERRED: 250,
}

HIGH_IMPACT_OPTIONAL_THRESHOLD = 50
INTERMEDIATE_PRIORITY_LIMIT = 12
DATASET_SCHEMA_SLOT_IDS = frozenset(
    {
        "target_column",
        "time_column",
        "dataset_type",
        "series_id_columns",
        "hierarchy_columns",
        "aggregation_level",
    }
)
CATALOG_DATASET_DETAIL_SLOT_IDS = frozenset(
    {
        "frequency",
        "dataset_type",
        "source_provider",
        "contains_sensitive_data",
    }
)
INTERMEDIATE_CORE_SLOT_IDS = (
    "problem_statement",
    "target_description",
    "target_unit",
    "frequency",
    "forecast_horizon",
    "dataset_type",
    "source_mode",
    "output_granularity",
    "contains_sensitive_data",
)


class ClarificationCandidate(BaseModel):
    slot_id: str
    reason: str
    score: int = Field(ge=0)


def catalog_dataset_schema_deferred(state: DialogueState, slot_id: str) -> bool:
    """Keep dataset-shape questions closed until a catalog item supplies its schema."""
    source_slot = state.slots.get("source_mode")
    source_mode = source_slot.value if source_slot is not None else None
    return (
        slot_id in DATASET_SCHEMA_SLOT_IDS
        and source_mode == "catalog"
        and not state.dataset_columns
    )


def catalog_dataset_detail_deferred(state: DialogueState, slot_id: str) -> bool:
    """Keep catalog-provided facts closed until a catalog item is selected."""
    source_slot = state.slots.get("source_mode")
    source_mode = source_slot.value if source_slot is not None else None
    return (
        slot_id in CATALOG_DATASET_DETAIL_SLOT_IDS
        and source_mode == "catalog"
        and not state.dataset_columns
    )


def _is_required(definition: SlotDefinition, state: DialogueState) -> bool:
    if (
        catalog_dataset_schema_deferred(state, definition.slot_id)
        or catalog_dataset_detail_deferred(state, definition.slot_id)
    ):
        return False
    return definition.requiredness == Requiredness.REQUIRED or (
        definition.requiredness == Requiredness.CONDITIONAL
        and is_slot_active(definition, state)
    )


def _is_unresolved(status: SlotStatus, confirmed_by_user: bool) -> bool:
    if status in {
        SlotStatus.UNMENTIONED,
        SlotStatus.AMBIGUOUS,
        SlotStatus.CONFLICTING,
        SlotStatus.INVALID,
        SlotStatus.DONT_CARE,
    }:
        return True
    return status == SlotStatus.INFERRED and not confirmed_by_user


def intermediate_core_slot_ids(
    schema: ForecastingSchema, state: DialogueState
) -> tuple[str, ...]:
    """Return the requirements needed for a useful intermediate forecast brief."""
    schema_slot_ids = {definition.slot_id for definition in schema.slots}
    slot_ids = [
        slot_id
        for slot_id in INTERMEDIATE_CORE_SLOT_IDS
        if (
            slot_id in schema_slot_ids
            and is_slot_active(schema.get(slot_id), state)
            and not catalog_dataset_schema_deferred(state, slot_id)
            and not catalog_dataset_detail_deferred(state, slot_id)
        )
    ]
    source_slot = state.slots.get("source_mode")
    source_mode = source_slot.value if source_slot is not None else None
    if source_mode in {"upload", "api", "database"} and "source_reference" in schema_slot_ids:
        slot_ids.append("source_reference")
    if state.dataset_columns or source_mode == "upload":
        slot_ids.extend(
            slot_id for slot_id in ("target_column", "time_column") if slot_id in schema_slot_ids
        )
    dataset_slot = state.slots.get("dataset_type")
    dataset_type = dataset_slot.value if dataset_slot is not None else None
    if dataset_type in {"panel", "hierarchical"} and "series_id_columns" in schema_slot_ids:
        slot_ids.append("series_id_columns")
    if dataset_type == "hierarchical" and "hierarchy_columns" in schema_slot_ids:
        slot_ids.append("hierarchy_columns")
    return tuple(slot_id for slot_id in slot_ids if slot_id in state.slots)


def rank_priority_slots(
    schema: ForecastingSchema, state: DialogueState
) -> list[dict[str, Any]]:
    """Rank unresolved requirements supplied to the provider for intermediate mode."""
    issues_by_slot: dict[str, list[ValidationIssue]] = {}
    for issue in validate_dialogue(schema, state):
        if issue.blocking and issue.slot_id is not None:
            issues_by_slot.setdefault(issue.slot_id, []).append(issue)

    candidates: list[tuple[int, int, SlotDefinition, SlotStatus]] = []
    core_ids = set(intermediate_core_slot_ids(schema, state))
    pruned_slots = gate_pruned_slots(schema, state)
    for definition in schema.slots:
        if not is_slot_active(definition, state):
            continue
        if definition.slot_id in pruned_slots:
            continue
        required = _is_required(definition, state)
        high_impact_optional = (
            definition.requiredness == Requiredness.OPTIONAL
            and definition.priority_weight >= HIGH_IMPACT_OPTIONAL_THRESHOLD
        )
        if not (required or high_impact_optional or definition.slot_id in core_ids):
            continue
        status = _candidate_status(definition, state, issues_by_slot)
        if status is None:
            continue
        score = STATUS_WEIGHTS[status] + definition.priority_weight + relevance_bonus(definition, state)
        candidates.append((score, definition.priority_weight, definition, status))

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2].slot_id))
    return [
        {
            "rank": rank,
            "slot_id": definition.slot_id,
            "description": definition.description,
            "question": definition.static_question,
            "priority": definition.priority_weight,
            "status": status.value,
            "aspect": ontology_path(definition).aspect,
            "dimension": ontology_path(definition).dimension,
            "gate_status": "eligible",
        }
        for rank, (_, _, definition, status) in enumerate(
            candidates[:INTERMEDIATE_PRIORITY_LIMIT], start=1
        )
    ]


def _intermediate_unresolved_slots(
    schema: ForecastingSchema,
    state: DialogueState,
    issues_by_slot: dict[str, list[ValidationIssue]],
) -> list[str]:
    unresolved: list[str] = []
    for slot_id in intermediate_core_slot_ids(schema, state):
        slot = state.slots[slot_id]
        if _is_unresolved(slot.status, slot.confirmed_by_user) or issues_by_slot.get(slot_id):
            unresolved.append(slot_id)
    if state.intent != Intent.CREATE_FORECAST:
        unresolved.insert(0, "intent")
    return unresolved


def evaluate_readiness(
    schema: ForecastingSchema, state: DialogueState
) -> ReadinessReport:
    issues = validate_dialogue(schema, state)
    active_required_slots: list[str] = []
    unresolved_slots: list[str] = []

    for definition in schema.slots:
        if not is_slot_active(definition, state):
            continue
        slot = state.slots.get(definition.slot_id)
        if _is_required(definition, state):
            active_required_slots.append(definition.slot_id)
            if slot is None or _is_unresolved(slot.status, slot.confirmed_by_user):
                unresolved_slots.append(definition.slot_id)
        elif (
            (
                definition.requiredness == Requiredness.OPTIONAL
                and definition.priority_weight >= HIGH_IMPACT_OPTIONAL_THRESHOLD
                and (slot is None or _is_unresolved(slot.status, slot.confirmed_by_user))
            )
            or (
                slot is not None
                and slot.status
                in {SlotStatus.AMBIGUOUS, SlotStatus.CONFLICTING, SlotStatus.INVALID}
            )
        ):
            unresolved_slots.append(definition.slot_id)

    blocking_issue_slots = {
        issue.slot_id for issue in issues if issue.blocking and issue.slot_id is not None
    }
    for slot_id in blocking_issue_slots:
        if slot_id not in unresolved_slots:
            unresolved_slots.append(slot_id)

    if state.intent != Intent.CREATE_FORECAST:
        issues = [
            *issues,
            ValidationIssue(
                slot_id="intent",
                code="forecasting_intent_required",
                message="A create_forecast intent must be confirmed before completion.",
            ),
        ]
        if "intent" not in unresolved_slots:
            unresolved_slots.insert(0, "intent")

    issues_by_slot: dict[str, list[ValidationIssue]] = {}
    for issue in issues:
        if issue.blocking and issue.slot_id is not None:
            issues_by_slot.setdefault(issue.slot_id, []).append(issue)
    core_slot_ids = intermediate_core_slot_ids(schema, state)
    intermediate_unresolved = _intermediate_unresolved_slots(schema, state, issues_by_slot)
    intermediate_blocked = any(
        issue.slot_id in set(core_slot_ids)
        for issue in issues
        if issue.blocking
    )
    if (
        core_slot_ids
        and state.intent == Intent.CREATE_FORECAST
        and not intermediate_unresolved
        and not intermediate_blocked
    ):
        return ReadinessReport(
            ready=True,
            active_required_slots=active_required_slots,
            unresolved_slots=unresolved_slots,
            issues=issues,
        )

    return ReadinessReport(
        ready=not unresolved_slots and not any(issue.blocking for issue in issues),
        active_required_slots=active_required_slots,
        unresolved_slots=unresolved_slots,
        issues=issues,
    )


def _candidate_status(
    definition: SlotDefinition,
    state: DialogueState,
    issues_by_slot: dict[str, list[ValidationIssue]],
) -> SlotStatus | None:
    slot = state.slots.get(definition.slot_id)
    if slot is None:
        return SlotStatus.UNMENTIONED
    if issues_by_slot.get(definition.slot_id):
        return SlotStatus.INVALID
    if slot.status in STATUS_WEIGHTS:
        if slot.status == SlotStatus.INFERRED and slot.confirmed_by_user:
            return None
        return slot.status
    return None


def _reason(
    definition: SlotDefinition,
    status: SlotStatus,
    issues: list[ValidationIssue],
) -> str:
    if issues:
        return f"invalid: {issues[0].message}"
    if status == SlotStatus.UNMENTIONED:
        label = "conditional" if definition.requiredness == Requiredness.CONDITIONAL else "required"
        if definition.requiredness == Requiredness.OPTIONAL:
            label = "high-impact optional"
        return f"missing {label} slot"
    if status == SlotStatus.INFERRED:
        return "inferred value requires user confirmation"
    return f"{status.value} value requires clarification"


def select_next_slot(
    schema: ForecastingSchema, state: DialogueState
) -> ClarificationCandidate | None:
    issues_by_slot: dict[str, list[ValidationIssue]] = {}
    for issue in validate_dialogue(schema, state):
        if issue.blocking and issue.slot_id is not None:
            issues_by_slot.setdefault(issue.slot_id, []).append(issue)

    if state.intent == Intent.CREATE_FORECAST:
        pruned_slots = gate_pruned_slots(schema, state)
        for source_slot_id in ("source_mode", "source_reference"):
            if source_slot_id in pruned_slots:
                continue
            try:
                definition = schema.get(source_slot_id)
            except KeyError:
                continue
            if not is_slot_active(definition, state):
                continue
            status = _candidate_status(definition, state, issues_by_slot)
            if status is None:
                continue
            return ClarificationCandidate(
                slot_id=source_slot_id,
                reason=_reason(definition, status, issues_by_slot.get(source_slot_id, [])),
                score=STATUS_WEIGHTS[status] + definition.priority_weight + 300,
            )

        core_ids = set(intermediate_core_slot_ids(schema, state))
        pruned_slots = gate_pruned_slots(schema, state)
        core_candidates: list[ClarificationCandidate] = []
        for definition in schema.slots:
            if (
                definition.slot_id not in core_ids
                or definition.slot_id in pruned_slots
                or not is_slot_active(definition, state)
            ):
                continue
            status = _candidate_status(definition, state, issues_by_slot)
            if status is None:
                continue
            core_candidates.append(
                ClarificationCandidate(
                    slot_id=definition.slot_id,
                    reason=_reason(definition, status, issues_by_slot.get(definition.slot_id, [])),
                    score=STATUS_WEIGHTS[status] + definition.priority_weight,
                )
            )
        if core_candidates:
            return max(core_candidates, key=lambda candidate: candidate.score)

    best: ClarificationCandidate | None = None
    for definition in schema.slots:
        if not is_slot_active(definition, state):
            continue
        required = _is_required(definition, state)
        high_impact_optional = (
            definition.requiredness == Requiredness.OPTIONAL
            and definition.priority_weight >= HIGH_IMPACT_OPTIONAL_THRESHOLD
        )
        status = _candidate_status(definition, state, issues_by_slot)
        if status is None or not (required or high_impact_optional or issues_by_slot.get(definition.slot_id)):
            continue

        score = STATUS_WEIGHTS[status] + definition.priority_weight + relevance_bonus(definition, state)
        if definition.requiredness == Requiredness.REQUIRED:
            score += 200
        elif definition.requiredness == Requiredness.CONDITIONAL:
            score += 100
        candidate = ClarificationCandidate(
            slot_id=definition.slot_id,
            reason=_reason(definition, status, issues_by_slot.get(definition.slot_id, [])),
            score=score,
        )
        if best is None or candidate.score > best.score:
            best = candidate
    return best
