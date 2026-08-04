from uuid import UUID

import pytest

from forecasting_assistant.application.orchestrator import ElicitationEngine
from forecasting_assistant.domain.models import (
    ExtractorResult,
    Intent,
    QuestionOutput,
    SlotStatus,
    SlotUpdate,
)
from forecasting_assistant.domain.schema import load_schema
from tests.fakes import FakeLLMClient, InMemoryDialogueRepository


MESSAGE = "complete forecasting requirements"


def _update(slot_id: str, value: object, *, evidence: str = "complete") -> SlotUpdate:
    return SlotUpdate(
        slot_id=slot_id,
        candidate_value=value,
        status=SlotStatus.PROVIDED,
        confidence=0.99,
        evidence_text=evidence,
    )


def _complete_result(*, omit: set[str] = set(), correction: bool = False) -> ExtractorResult:
    values = {
        "intent": "create_forecast",
        "problem_statement": "monthly sales",
        "business_goal": "inventory planning",
        "success_criteria": "lower MAE",
        "target_column": "revenue",
        "target_description": "monthly sales revenue",
        "target_unit": "PKR",
        "time_column": "month",
        "frequency": {"periods": 1, "unit": "month"},
        "forecast_horizon": {"periods": 12, "unit": "month"},
        "dataset_type": "single_series",
        "source_mode": "upload",
        "source_reference": "sales.xlsx",
        "file_format": "xlsx",
        "sheet_or_table": "Sheet1",
        "forecast_type": "point",
        "output_granularity": "monthly",
        "primary_metric": "mae",
        "contains_sensitive_data": False,
    }
    return ExtractorResult(
        intent=Intent.CREATE_FORECAST,
        intent_confidence=0.99,
        correction_detected=correction,
        updates=[_update(slot_id, value) for slot_id, value in values.items() if slot_id not in omit],
    )


async def _start(client: FakeLLMClient):
    repository = InMemoryDialogueRepository()
    engine = ElicitationEngine(load_schema(), client, repository)
    state = engine.start_dialogue()
    return engine, repository, state.dialogue_id


@pytest.mark.asyncio
async def test_complete_prompt_returns_confirmation_summary() -> None:
    engine, repository, dialogue_id = await _start(FakeLLMClient([_complete_result()]))

    result = await engine.handle_user_message(dialogue_id, MESSAGE)

    assert result.readiness.ready
    assert result.specification is None
    assert "confirm" in result.assistant_message.lower()
    assert repository.load_state(dialogue_id).turns[-1].assistant_message == result.assistant_message


@pytest.mark.asyncio
async def test_missing_target_asks_exactly_one_target_question() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"target_column"})],
        [QuestionOutput(question="Which target column should be forecast?")],
    )
    engine, _, dialogue_id = await _start(client)

    result = await engine.handle_user_message(dialogue_id, MESSAGE)

    assert not result.readiness.ready
    assert result.assistant_message == "Which target column should be forecast?"
    assert client.ask_requests[0].slot_id == "target_column"


@pytest.mark.asyncio
async def test_invalid_generated_question_retries_once_then_uses_valid_output() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"target_column"})],
        [
            QuestionOutput(question="What is the target? What is the horizon?"),
            QuestionOutput(question="Which target column should be forecast?"),
        ],
    )
    engine, _, dialogue_id = await _start(client)

    result = await engine.handle_user_message(dialogue_id, MESSAGE)

    assert result.assistant_message == "Which target column should be forecast?"
    assert len(client.ask_requests) == 2


@pytest.mark.asyncio
async def test_target_answer_updates_state_and_reaches_summary() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"target_column"}),
            ExtractorResult(
                intent=Intent.CREATE_FORECAST,
                intent_confidence=0.99,
                updates=[_update("target_column", "revenue", evidence="revenue")],
            ),
        ],
        [QuestionOutput(question="Which target column should be forecast?")],
    )
    engine, _, dialogue_id = await _start(client)
    await engine.handle_user_message(dialogue_id, MESSAGE)

    result = await engine.handle_user_message(dialogue_id, "revenue")

    assert result.readiness.ready
    assert result.state.slots["target_column"].value == "revenue"


@pytest.mark.asyncio
async def test_explicit_correction_updates_summary() -> None:
    correction = ExtractorResult(
        intent=Intent.CREATE_FORECAST,
        intent_confidence=0.99,
        correction_detected=True,
        updates=[
            _update("frequency", {"periods": 1, "unit": "week"}, evidence="weekly"),
            _update("output_granularity", "weekly", evidence="weekly"),
        ],
    )
    client = FakeLLMClient([_complete_result(), correction])
    engine, _, dialogue_id = await _start(client)
    await engine.handle_user_message(dialogue_id, MESSAGE)

    result = await engine.handle_user_message(dialogue_id, "Change it to weekly")

    assert result.state.slots["frequency"].value == {"periods": 1, "unit": "week"}
    assert "week" in result.assistant_message.lower()


@pytest.mark.asyncio
async def test_explicit_confirmation_builds_specification() -> None:
    engine, repository, dialogue_id = await _start(FakeLLMClient([_complete_result()]))
    await engine.handle_user_message(dialogue_id, MESSAGE)

    specification = engine.confirm_specification(dialogue_id, confirm=True)

    assert specification.dialogue_id == dialogue_id
    assert specification.values["target_column"] == "revenue"
    assert repository.load_state(dialogue_id).confirmed
    assert repository.specifications[dialogue_id] == specification


@pytest.mark.asyncio
async def test_provider_failure_uses_static_question_without_slot_mutation() -> None:
    engine, repository, dialogue_id = await _start(FakeLLMClient())
    before = repository.load_state(dialogue_id).model_copy(deep=True)

    result = await engine.handle_user_message(dialogue_id, "I need a forecast")

    assert result.assistant_message == load_schema().get("intent").static_question
    assert result.state.slots == before.slots


@pytest.mark.asyncio
async def test_selected_enum_answer_recovers_when_extractor_fails() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"source_mode"})],
        [QuestionOutput(question="Will the data be uploaded, read from an API, read from a database, or selected from a catalog?")],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    assert first.assistant_message == "Will the data be uploaded, read from an API, read from a database, or selected from a catalog?"

    result = await engine.handle_user_message(dialogue_id, "upload")

    assert result.state.slots["source_mode"].value == "upload"
    assert result.state.slots["source_mode"].status == SlotStatus.PROVIDED
    assert result.readiness.ready
    assert "confirm" in result.assistant_message.lower()


@pytest.mark.asyncio
async def test_selected_boolean_answer_recovers_when_extractor_fails() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"contains_sensitive_data"})],
        [
            QuestionOutput(
                question="Does the source contain personal, confidential, or regulated data?"
            ),
            QuestionOutput(question="Which privacy or access restrictions apply?"),
        ],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    assert first.assistant_message == "Does the source contain personal, confidential, or regulated data?"

    result = await engine.handle_user_message(dialogue_id, "yes")

    assert result.state.slots["contains_sensitive_data"].value is True
    assert result.state.slots["contains_sensitive_data"].status == SlotStatus.PROVIDED
    assert result.assistant_message == "Which privacy or access restrictions apply?"


@pytest.mark.asyncio
async def test_selected_boolean_answer_overrides_bad_not_forecasting_intent() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"contains_sensitive_data"}),
            ExtractorResult(
                intent=Intent.NOT_FORECASTING,
                intent_confidence=0.8,
                updates=[
                    _update(
                        "intent",
                        "not_forecasting",
                        evidence="no",
                    )
                ],
            ),
        ],
        [QuestionOutput(question="Does the source contain personal, confidential, or regulated data?")],
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "no")

    assert result.state.intent == Intent.CREATE_FORECAST
    assert result.state.slots["contains_sensitive_data"].value is False
    assert result.state.slots["contains_sensitive_data"].status == SlotStatus.PROVIDED
    assert "supports time-series forecasting requirements only" not in result.assistant_message


@pytest.mark.asyncio
async def test_selected_intent_question_accepts_yes_confirmation() -> None:
    initial_result = _complete_result(omit={"intent"})
    initial_result.intent = Intent.AMBIGUOUS
    initial_result.intent_confidence = 0.4
    client = FakeLLMClient(
        [
            initial_result,
            ExtractorResult(intent=Intent.AMBIGUOUS, intent_confidence=0.4),
        ],
        [QuestionOutput(question="Do you want the system to create a time-series forecast?")],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    second = await engine.handle_user_message(dialogue_id, "yes")

    assert first.assistant_message == "Do you want the system to create a time-series forecast?"
    assert second.state.intent == Intent.CREATE_FORECAST
    assert second.state.slots["intent"].value == Intent.CREATE_FORECAST.value
    assert second.state.slots["intent"].status == SlotStatus.PROVIDED
    assert second.assistant_message != "Do you want the system to create a time-series forecast?"


@pytest.mark.asyncio
async def test_unsupported_intent_returns_terminal_scope_message() -> None:
    unsupported = ExtractorResult(intent=Intent.NOT_FORECASTING, intent_confidence=0.99)
    engine, _, dialogue_id = await _start(FakeLLMClient([unsupported]))

    result = await engine.handle_user_message(dialogue_id, "Write me a poem")

    assert "forecast" in result.assistant_message.lower()
    assert not result.readiness.ready


def test_confirmation_requires_explicit_true() -> None:
    repository = InMemoryDialogueRepository()
    engine = ElicitationEngine(load_schema(), FakeLLMClient(), repository)
    dialogue_id: UUID = engine.start_dialogue().dialogue_id

    with pytest.raises(ValueError, match="explicit confirmation"):
        engine.confirm_specification(dialogue_id, confirm=False)
