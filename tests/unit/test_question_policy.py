import json

from forecasting_assistant.domain.models import QuestionOutput, QuestionRequest, SlotState
from forecasting_assistant.prompts.llmrei_long import (
    build_question_input,
    build_question_instructions,
    static_fallback_question,
    validate_question,
)


def _request(**changes: object) -> QuestionRequest:
    values = {
        "slot_id": "frequency",
        "reason": "required slot is missing",
        "slot_description": "Native observation frequency.",
        "current_state": SlotState(slot_id="frequency"),
        "confirmed_context": {"target_description": "sales"},
        "static_question": "How often are sales observed?",
        "allowed_values": ("daily", "weekly", "monthly"),
        "other_active_slot_ids": ("forecast_horizon", "target_column"),
    }
    values.update(changes)
    return QuestionRequest(**values)


def test_rejects_multiple_or_missing_question_marks() -> None:
    assert not validate_question(
        QuestionOutput(question="How often are sales measured? Is it daily?"), _request()
    )
    assert not validate_question(QuestionOutput(question="Tell me the frequency."), _request())


def test_rejects_question_that_suggests_unconfirmed_value() -> None:
    assert not validate_question(
        QuestionOutput(question="Should the frequency be weekly?"), _request()
    )


def test_allows_candidate_already_present_in_confirmed_context() -> None:
    request = _request(confirmed_context={"frequency": "weekly", "target": "sales"})
    assert validate_question(QuestionOutput(question="Is weekly still the frequency?"), request)


def test_rejects_different_active_slot() -> None:
    output = QuestionOutput(question="What is the forecast horizon?")
    assert not validate_question(output, _request())


def test_accepts_one_bounded_selected_slot_question() -> None:
    output = QuestionOutput(question="How often are sales observations recorded?")
    assert validate_question(output, _request())


def test_static_fallback_uses_schema_wording() -> None:
    assert static_fallback_question(_request()).question == "How often are sales observed?"


def test_question_instructions_include_llmrei_long_behaviors() -> None:
    instructions = build_question_instructions().lower()
    assert "exactly one" in instructions
    assert "do not assume" in instructions
    assert "selected slot" in instructions
    assert "do not ask about any other slot" in instructions


def test_question_input_redacts_provider_bound_credentials() -> None:
    request = _request(
        confirmed_context={"source": "api_key=super-secret", "target": "sales"}
    )

    payload = json.loads(build_question_input(request))

    assert "super-secret" not in json.dumps(payload)
    assert payload["confirmed_context"]["target"] == "sales"
