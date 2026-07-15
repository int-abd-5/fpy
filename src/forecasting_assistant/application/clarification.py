from __future__ import annotations

from pydantic import BaseModel, Field

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


class ClarificationCandidate(BaseModel):
    slot_id: str
    reason: str
    score: int = Field(ge=0)


def _is_required(definition: SlotDefinition, state: DialogueState) -> bool:
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
            definition.requiredness == Requiredness.OPTIONAL
            and definition.priority_weight >= HIGH_IMPACT_OPTIONAL_THRESHOLD
            and (slot is None or _is_unresolved(slot.status, slot.confirmed_by_user))
        ):
            unresolved_slots.append(definition.slot_id)
        elif slot is not None and slot.status in {
            SlotStatus.AMBIGUOUS,
            SlotStatus.CONFLICTING,
            SlotStatus.INVALID,
        }:
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

        score = STATUS_WEIGHTS[status] + definition.priority_weight
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
