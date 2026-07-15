from copy import deepcopy

import pytest

from forecasting_assistant.application.state_reducer import (
    UnsupportedEvidenceError,
    UnknownSlotError,
    apply_extraction,
)
from forecasting_assistant.domain.models import (
    ExtractorResult,
    Intent,
    SlotState,
    SlotStatus,
    SlotUpdate,
)
from forecasting_assistant.domain.schema import ForecastingSchema, create_initial_state, load_schema


def _result(
    slot_id: str,
    value: object,
    *,
    correction: bool = False,
    evidence: str | None = None,
    status: SlotStatus = SlotStatus.PROVIDED,
    confidence: float = 0.95,
) -> ExtractorResult:
    return ExtractorResult(
        intent=Intent.CREATE_FORECAST,
        intent_confidence=0.99,
        correction_detected=correction,
        updates=[
            SlotUpdate(
                slot_id=slot_id,
                candidate_value=value,
                status=status,
                confidence=confidence,
                evidence_text=str(value) if evidence is None else evidence,
            )
        ],
    )


def _state_with_confirmed_frequency() -> tuple[object, object]:
    schema = load_schema()
    state = create_initial_state(schema)
    state.slots["frequency"] = SlotState(
        slot_id="frequency",
        value="daily",
        status=SlotStatus.CONFIRMED,
        confidence=1.0,
        evidence_text="daily",
        source_turn=1,
        confirmed_by_user=True,
    )
    return schema, state


def test_confirmed_value_is_not_overwritten_without_correction_intent() -> None:
    schema, state = _state_with_confirmed_frequency()
    updated = apply_extraction(state, _result("frequency", "weekly"), schema, 2, "weekly")

    assert updated.slots["frequency"].value == "daily"
    assert updated.slots["frequency"].status == SlotStatus.CONFLICTING


def test_explicit_correction_replaces_value_and_clears_confirmation() -> None:
    schema, state = _state_with_confirmed_frequency()
    updated = apply_extraction(
        state,
        _result("frequency", "weekly", correction=True),
        schema,
        2,
        "weekly",
    )

    assert updated.slots["frequency"].value == "weekly"
    assert updated.slots["frequency"].status == SlotStatus.INVALID
    assert not updated.slots["frequency"].confirmed_by_user


def test_same_confirmed_value_preserves_confirmation_and_status() -> None:
    schema, state = _state_with_confirmed_frequency()

    updated = apply_extraction(state, _result("frequency", "daily"), schema, 2, "daily")

    assert updated.slots["frequency"].value == "daily"
    assert updated.slots["frequency"].status == SlotStatus.CONFIRMED
    assert updated.slots["frequency"].confirmed_by_user


def test_extractor_confirmed_status_is_downgraded_without_user_confirmation() -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    updated = apply_extraction(
        state,
        _result("forecast_type", "point", status=SlotStatus.CONFIRMED),
        schema,
        1,
        "point",
    )

    assert updated.slots["forecast_type"].status == SlotStatus.PROVIDED
    assert not updated.slots["forecast_type"].confirmed_by_user


def test_unknown_slot_update_is_rejected() -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    with pytest.raises(UnknownSlotError):
        apply_extraction(state, _result("made_up_slot", "x"), schema, 1, "x")


def test_state_slot_not_registered_in_schema_is_rejected_as_unknown() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.slots["forged_slot"] = SlotState(slot_id="forged_slot")

    with pytest.raises(UnknownSlotError):
        apply_extraction(state, _result("forged_slot", "x"), schema, 1, "x")


def test_schema_slot_missing_from_state_is_rejected_as_unknown() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    drifted_schema = ForecastingSchema(
        slots=tuple(slot for slot in schema.slots if slot.slot_id != "frequency")
    )

    with pytest.raises(UnknownSlotError):
        apply_extraction(state, _result("frequency", "daily"), drifted_schema, 1, "daily")


def test_invalid_value_is_recorded_without_becoming_confirmed() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    updated = apply_extraction(
        state,
        _result("minimum_coverage", 150),
        schema,
        1,
        "150",
    )

    assert updated.slots["minimum_coverage"].status == SlotStatus.INVALID
    assert updated.slots["minimum_coverage"].validation_errors
    assert not updated.slots["minimum_coverage"].confirmed_by_user


def test_assistant_suggestion_cannot_become_user_evidence() -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    with pytest.raises(UnsupportedEvidenceError):
        apply_extraction(state, _result("frequency", "weekly"), schema, 1, "I do not know")


def test_evidence_matching_is_case_insensitive_and_records_provenance() -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    updated = apply_extraction(
        state,
        _result("forecast_type", "POINT", evidence="point", confidence=0.72),
        schema,
        4,
        "I need POINT forecasts.",
    )

    slot = updated.slots["forecast_type"]
    assert slot.value == "point"
    assert slot.status == SlotStatus.PROVIDED
    assert slot.evidence_text == "point"
    assert slot.source_turn == 4
    assert slot.confidence == 0.72


@pytest.mark.parametrize("evidence", ["", "   ", "weekly"])
def test_blank_or_absent_evidence_is_rejected(evidence: str) -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    with pytest.raises(UnsupportedEvidenceError):
        apply_extraction(state, _result("frequency", "daily", evidence=evidence), schema, 1, "daily")


def test_repeated_unconfirmed_updates_replace_value() -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    first = apply_extraction(state, _result("frequency", {"periods": 1, "unit": "day"}, evidence="daily"), schema, 1, "daily")
    second = apply_extraction(first, _result("frequency", {"periods": 1, "unit": "week"}, evidence="weekly"), schema, 2, "weekly")

    assert second.slots["frequency"].value == {"periods": 1, "unit": "week"}
    assert second.slots["frequency"].status == SlotStatus.PROVIDED
    assert second.slots["frequency"].source_turn == 2


def test_valid_update_preserves_existing_validation_errors_only_when_conflicting() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.slots["frequency"] = SlotState(
        slot_id="frequency",
        value={"periods": 0, "unit": "day"},
        status=SlotStatus.INVALID,
        evidence_text="zero days",
        validation_errors=["old error"],
    )

    updated = apply_extraction(
        state,
        _result("frequency", {"periods": 1, "unit": "day"}, evidence="daily"),
        schema,
        2,
        "daily",
    )

    assert updated.slots["frequency"].value == {"periods": 1, "unit": "day"}
    assert updated.slots["frequency"].status == SlotStatus.PROVIDED
    assert updated.slots["frequency"].validation_errors == []


def test_multiple_updates_are_applied_in_order() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    result = ExtractorResult(
        intent=Intent.CREATE_FORECAST,
        intent_confidence=0.99,
        updates=[
            SlotUpdate(slot_id="frequency", candidate_value="daily", status=SlotStatus.PROVIDED, confidence=0.8, evidence_text="daily"),
            SlotUpdate(slot_id="forecast_type", candidate_value="POINT", status=SlotStatus.PROVIDED, confidence=0.7, evidence_text="point"),
        ],
    )

    updated = apply_extraction(state, result, schema, 3, "daily point forecast")

    assert updated.slots["frequency"].value == "daily"
    assert updated.slots["forecast_type"].value == "point"


def test_input_state_is_deeply_unchanged() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    before = deepcopy(state)

    updated = apply_extraction(state, _result("geography", ["PK"], evidence="PK"), schema, 1, "PK")

    assert state == before
    assert updated is not state
    assert updated.slots is not state.slots


def test_mutating_extractor_nested_candidate_does_not_mutate_returned_state() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    candidate = [{"field": "region", "values": ["PK", {"code": "ISB"}]}]
    result = _result("scope_filters", candidate, evidence="region")

    updated = apply_extraction(state, result, schema, 1, "region")
    candidate[0]["values"].append("US")
    candidate[0]["values"][1]["code"] = "LHR"

    assert updated.slots["scope_filters"].value == [
        {"field": "region", "values": ["PK", {"code": "ISB"}]}
    ]


def test_evidence_must_be_from_current_message_only_and_failure_is_atomic() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    before = deepcopy(state)
    result = ExtractorResult(
        intent=Intent.CREATE_FORECAST,
        intent_confidence=0.99,
        updates=[
            SlotUpdate(slot_id="frequency", candidate_value="daily", status=SlotStatus.PROVIDED, confidence=0.8, evidence_text="daily"),
            SlotUpdate(slot_id="forecast_type", candidate_value="point", status=SlotStatus.PROVIDED, confidence=0.7, evidence_text="weekly"),
        ],
    )

    with pytest.raises(UnsupportedEvidenceError):
        apply_extraction(state, result, schema, 2, "daily point forecast")

    assert state == before
