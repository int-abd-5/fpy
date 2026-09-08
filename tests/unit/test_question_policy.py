import json

import pytest

from forecasting_assistant.domain.models import QuestionOutput, QuestionRequest, SlotState
from forecasting_assistant.prompts.llmrei_long import (
    build_question_input,
    build_question_instructions,
    example_answer,
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


def test_allows_a_question_that_lists_unconfirmed_choices() -> None:
    request = _request(
        slot_id="source_mode",
        slot_description="How the data will be provided.",
        current_state=SlotState(slot_id="source_mode"),
        static_question="How will the data be provided?",
        allowed_values=("upload", "api", "database", "catalog"),
        other_active_slot_ids=("frequency", "target_column"),
    )

    assert validate_question(
        QuestionOutput(
            question=(
                "How will you provide the data: upload a file, connect via API, "
                "use a database, or choose from our catalog? Example answer: upload a file."
            )
        ),
        request,
    )


def test_allows_candidate_already_present_in_confirmed_context() -> None:
    request = _request(confirmed_context={"frequency": "weekly", "target": "sales"})
    assert validate_question(
        QuestionOutput(question="Is weekly still the frequency? Example answer: weekly."),
        request,
    )


def test_questions_require_an_illustrative_example_answer() -> None:
    request = _request()

    assert validate_question(
        QuestionOutput(question="How often are sales observations recorded? Example answer: daily."),
        request,
    )
    assert not validate_question(
        QuestionOutput(question="How often are sales observations recorded?"),
        request,
    )


def test_rejects_different_active_slot() -> None:
    output = QuestionOutput(question="What is the forecast horizon?")
    assert not validate_question(output, _request())


@pytest.mark.parametrize(
    ("request_changes", "question"),
    [
        ({}, "How often are sales observations recorded? Example answer: daily."),
        ({}, "What is the observation cadence for sales? Example answer: daily."),
        (
            {
                "slot_id": "forecast_horizon",
                "slot_description": "How far ahead to forecast.",
                "current_state": SlotState(slot_id="forecast_horizon"),
                "static_question": "How far ahead should sales be forecast?",
                "allowed_values": (),
                "other_active_slot_ids": ("frequency", "target_column"),
            },
            "How far ahead should sales be forecast? Example answer: 12 months.",
        ),
        (
            {
                "slot_id": "target_column",
                "slot_description": "Column containing the forecast target.",
                "current_state": SlotState(slot_id="target_column"),
                "static_question": "Which column contains the sales values?",
                "allowed_values": (),
                "other_active_slot_ids": ("frequency", "forecast_horizon"),
            },
            "Which column contains the sales values to forecast? Example answer: revenue.",
        ),
        (
            {
                "slot_id": "source_reference",
                "slot_description": "Reference to the source data.",
                "current_state": SlotState(slot_id="source_reference"),
                "static_question": "Where is the sales history located?",
                "allowed_values": (),
                "other_active_slot_ids": ("frequency", "forecast_horizon"),
            },
            "Where is the sales history located? Example answer: sales.xlsx.",
        ),
        (
            {
                "slot_id": "prediction_interval_levels",
                "slot_description": "Requested prediction interval levels.",
                "current_state": SlotState(slot_id="prediction_interval_levels"),
                "static_question": "Which prediction interval levels are required?",
                "allowed_values": (),
                "other_active_slot_ids": ("frequency", "forecast_horizon"),
            },
            "Which prediction interval levels should the sales forecast include? Example answer: 80% and 95%.",
        ),
    ],
    ids=(
        "frequency-natural-wording",
        "frequency-cadence-wording",
        "forecast-horizon",
        "target-column",
        "source-reference",
        "prediction-interval-levels",
    ),
)
def test_accepts_valid_bounded_selected_slot_questions(
    request_changes: dict[str, object], question: str
) -> None:
    assert validate_question(QuestionOutput(question=question), _request(**request_changes))


def test_static_fallback_uses_schema_wording() -> None:
    assert static_fallback_question(_request()).question == (
        "How often are sales observed? Example answer: once per day."
    )


def test_question_input_contains_the_selected_slot_example() -> None:
    payload = json.loads(build_question_input(_request()))

    assert payload["example_answer"] == "once per day"
    assert example_answer(_request()) == "once per day"


def test_question_input_contains_numbered_intermediate_priority_slots() -> None:
    request = _request(
        priority_slots=(
            {
                "rank": 1,
                "slot_id": "frequency",
                "question": "How often are sales observed?",
                "priority": 100,
                "status": "unmentioned",
            },
        )
    )

    payload = json.loads(build_question_input(request))

    assert payload["priority_slots"][0]["rank"] == 1


def test_question_instructions_include_llmrei_long_behaviors() -> None:
    instructions = build_question_instructions().lower()
    assert "exactly one" in instructions
    assert "do not assume" in instructions
    assert "selected slot" in instructions
    assert "do not ask about any other slot" in instructions
    assert "example answer" in instructions
    assert "everyday language" in instructions
    assert "point forecast" in instructions


def test_question_input_redacts_provider_bound_credentials() -> None:
    request = _request(
        confirmed_context={"source": "api_key=super-secret", "target": "sales"}
    )

    payload = json.loads(build_question_input(request))

    assert "super-secret" not in json.dumps(payload)
    assert payload["confirmed_context"]["target"] == "sales"
