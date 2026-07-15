from __future__ import annotations

from copy import deepcopy

from forecasting_assistant.application.normalization import normalize_value
from forecasting_assistant.application.validation import validate_slot
from forecasting_assistant.domain.models import DialogueState, ExtractorResult, SlotStatus
from forecasting_assistant.domain.schema import ForecastingSchema


class UnknownSlotError(ValueError):
    def __init__(self, slot_id: str) -> None:
        super().__init__(f"Unknown slot: {slot_id}")
        self.slot_id = slot_id


class UnsupportedEvidenceError(ValueError):
    def __init__(self, evidence_text: str) -> None:
        super().__init__("Extractor evidence must be a non-blank substring of the current message.")
        self.evidence_text = evidence_text


def _check_contract(
    state: DialogueState,
    result: ExtractorResult,
    schema: ForecastingSchema,
    current_message: str,
) -> None:
    message = current_message.casefold()
    schema_slot_ids = {slot.slot_id for slot in schema.slots}
    for update in result.updates:
        if update.slot_id not in state.slots or update.slot_id not in schema_slot_ids:
            raise UnknownSlotError(update.slot_id)
        if not update.evidence_text.strip() or update.evidence_text.casefold() not in message:
            raise UnsupportedEvidenceError(update.evidence_text)


def _apply_update(
    state: DialogueState,
    result: ExtractorResult,
    update,
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


def apply_extraction(
    state: DialogueState,
    result: ExtractorResult,
    schema: ForecastingSchema,
    turn_number: int,
    current_message: str,
) -> DialogueState:
    _check_contract(state, result, schema, current_message)
    updated_state = deepcopy(state)
    updated_state.intent = result.intent
    for update in result.updates:
        _apply_update(updated_state, result, update, schema, turn_number)
    return updated_state
