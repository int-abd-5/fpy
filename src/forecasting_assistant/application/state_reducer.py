from __future__ import annotations

from copy import deepcopy
import re

from forecasting_assistant.application.normalization import normalize_value
from forecasting_assistant.application.validation import validate_slot
from forecasting_assistant.domain.models import (
    DialogueState,
    ExtractorResult,
    Intent,
    SlotStatus,
    SlotUpdate,
)
from forecasting_assistant.domain.schema import ForecastingSchema


class UnknownSlotError(ValueError):
    def __init__(self, slot_id: str) -> None:
        super().__init__(f"Unknown slot: {slot_id}")
        self.slot_id = slot_id


class UnsupportedEvidenceError(ValueError):
    def __init__(self, evidence_text: str) -> None:
        super().__init__("Extractor evidence must be a non-blank substring of the current message.")
        self.evidence_text = evidence_text


_FORECAST_TERM_PATTERN = re.compile(
    r"\b(?:forecast(?:ing)?|predict(?:ion|ed|ing)?|project(?:ion|ed|ing)?|"
    r"estimate(?:d|s|ing)?|time[- ]series)\b",
    re.IGNORECASE,
)
_EXPLICIT_FORECAST_REQUEST_PATTERN = re.compile(
    r"\b(?:i|we)\s+(?:want|need|would like|am looking to|am looking for)\b"
    r".{0,100}\b(?:forecast|predict(?:ion|ed|ing)?|project(?:ion|ed|ing)?|"
    r"estimate(?:d|s|ing)?|time[- ]series)\b",
    re.IGNORECASE,
)


def _check_contract(
    state: DialogueState,
    result: ExtractorResult,
    schema: ForecastingSchema,
    current_message: str,
) -> list[SlotUpdate]:
    message = current_message.casefold()
    schema_slot_ids = {slot.slot_id for slot in schema.slots}
    valid_updates: list[SlotUpdate] = []
    invalid_evidence: str | None = None
    for update in result.updates:
        if update.slot_id not in state.slots or update.slot_id not in schema_slot_ids:
            raise UnknownSlotError(update.slot_id)
        if update.status in {SlotStatus.UNMENTIONED, SlotStatus.DONT_CARE}:
            continue
        evidence = _canonical_evidence(update, current_message, message)
        if evidence is None:
            invalid_evidence = invalid_evidence or update.evidence_text
            continue
        valid_updates.append(update.model_copy(update={"evidence_text": evidence}))
    if invalid_evidence is not None and not valid_updates:
        raise UnsupportedEvidenceError(invalid_evidence)
    return valid_updates


def _canonical_evidence(
    update: SlotUpdate, current_message: str, folded_message: str
) -> str | None:
    evidence = update.evidence_text.strip()
    if not evidence:
        return None

    if evidence and evidence.casefold() in folded_message:
        return evidence

    quoted_message = re.search(r"user message:\s*[\"'](?P<text>.*?)[\"']\s*$", evidence, re.IGNORECASE)
    if quoted_message is not None:
        snippet = quoted_message.group("text").strip()
        compact = re.sub(r"\.{3,}", "", snippet).strip()
        if compact and compact.casefold() in folded_message:
            return current_message

    candidate = update.candidate_value
    if (
        ("user message" in evidence.casefold() or "..." in evidence)
        and isinstance(candidate, str)
        and candidate.strip()
        and candidate.casefold() in folded_message
    ):
        return candidate.strip()
    return None


def _resolved_intent(
    state: DialogueState,
    result: ExtractorResult,
    valid_updates: list[SlotUpdate],
    current_message: str,
) -> Intent:
    if state.intent == Intent.CREATE_FORECAST or result.intent == Intent.CREATE_FORECAST:
        return Intent.CREATE_FORECAST
    if result.intent in {Intent.NOT_FORECASTING, Intent.UNSUPPORTED}:
        return result.intent

    existing_intent = state.slots["intent"]
    if (
        existing_intent.value == Intent.CREATE_FORECAST.value
        and existing_intent.status not in {SlotStatus.INVALID, SlotStatus.CONFLICTING}
    ):
        return Intent.CREATE_FORECAST

    forecast_statements = [
        str(update.candidate_value)
        for update in valid_updates
        if update.slot_id == "problem_statement"
        and update.status in {SlotStatus.PROVIDED, SlotStatus.INFERRED, SlotStatus.CONFIRMED}
    ]
    has_forecast_statement = any(_FORECAST_TERM_PATTERN.search(value) for value in forecast_statements)
    has_explicit_request = _EXPLICIT_FORECAST_REQUEST_PATTERN.search(current_message) is not None
    if result.intent == Intent.AMBIGUOUS and (has_forecast_statement or has_explicit_request):
        return Intent.CREATE_FORECAST
    return result.intent


def _apply_update(
    state: DialogueState,
    result: ExtractorResult,
    update: SlotUpdate,
    schema: ForecastingSchema,
    turn_number: int,
) -> None:
    current = state.slots[update.slot_id]
    definition = schema.get(update.slot_id)
    normalized = deepcopy(normalize_value(definition, update.candidate_value))

    if current.confirmed_by_user and current.value != normalized and not result.correction_detected:
        current.status = SlotStatus.CONFLICTING
        current.confidence = update.confidence
        current.evidence_text = update.evidence_text
        current.source_turn = turn_number
        return

    if current.confirmed_by_user and current.value == normalized and not result.correction_detected:
        current.status = SlotStatus.CONFIRMED
        current.confidence = update.confidence
        current.evidence_text = update.evidence_text
        current.source_turn = turn_number
        return

    current.value = normalized
    current.status = SlotStatus.PROVIDED if update.status == SlotStatus.CONFIRMED else update.status
    current.confidence = update.confidence
    current.evidence_text = update.evidence_text
    current.source_turn = turn_number
    current.confirmed_by_user = False
    current.validation_errors = [issue.message for issue in validate_slot(definition, current)]
    if current.validation_errors:
        current.status = SlotStatus.INVALID
    elif (
        definition.value_type == "duration"
        and isinstance(normalized, dict)
        and update.status in {SlotStatus.AMBIGUOUS, SlotStatus.INVALID}
    ):
        current.status = SlotStatus.PROVIDED


def apply_extraction(
    state: DialogueState,
    result: ExtractorResult,
    schema: ForecastingSchema,
    turn_number: int,
    current_message: str,
) -> DialogueState:
    valid_updates = _check_contract(state, result, schema, current_message)
    updated_state = deepcopy(state)
    resolved_intent = _resolved_intent(state, result, valid_updates, current_message)
    forecasting_intent_locked = state.intent == Intent.CREATE_FORECAST
    updated_state.intent = resolved_intent
    for update in valid_updates:
        _apply_update(updated_state, result, update, schema, turn_number)
    if forecasting_intent_locked:
        updated_state.slots["intent"] = deepcopy(state.slots["intent"])
    elif resolved_intent == Intent.CREATE_FORECAST:
        intent_slot = updated_state.slots["intent"]
        intent_update = next(
            (update for update in valid_updates if update.slot_id == "intent"),
            None,
        )
        intent_slot.value = Intent.CREATE_FORECAST.value
        intent_slot.status = (
            SlotStatus.CONFIRMED if intent_slot.confirmed_by_user else SlotStatus.PROVIDED
        )
        intent_slot.confidence = result.intent_confidence
        intent_slot.evidence_text = (
            intent_update.evidence_text if intent_update is not None else current_message
        )
        intent_slot.source_turn = turn_number
        intent_slot.validation_errors = []
    return updated_state
