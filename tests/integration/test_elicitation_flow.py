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
from forecasting_assistant.infrastructure.llm.openai_responses import LLMContractError
from tests.fakes import FakeLLMClient, InMemoryDialogueRepository

MESSAGE = "complete forecasting requirements"


def _update(
    slot_id: str,
    value: object,
    *,
    evidence: str = "complete",
    status: SlotStatus = SlotStatus.PROVIDED,
) -> SlotUpdate:
    return SlotUpdate(
        slot_id=slot_id,
        candidate_value=value,
        status=status,
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


def test_attaching_uploaded_file_records_source_and_columns() -> None:
    repository = InMemoryDialogueRepository()
    engine = ElicitationEngine(load_schema(), FakeLLMClient(), repository)
    state = engine.start_dialogue()

    updated = engine.attach_uploaded_file(
        state.dialogue_id,
        source_reference="dataset_store/uploads/sales.csv",
        filename="sales.csv",
        columns=["date", "region", "revenue"],
    )

    assert updated.dataset_columns == ["date", "region", "revenue"]
    assert updated.slots["source_mode"].value == "upload"
    assert updated.slots["source_reference"].value == "dataset_store/uploads/sales.csv"
    assert updated.slots["file_format"].value == "csv"


@pytest.mark.asyncio
async def test_complete_prompt_returns_confirmation_summary() -> None:
    engine, repository, dialogue_id = await _start(FakeLLMClient([_complete_result()]))

    result = await engine.handle_user_message(dialogue_id, MESSAGE)

    assert result.readiness.ready
    assert result.specification is None
    assert "confirm" in result.assistant_message.lower()
    assert repository.load_state(dialogue_id).turns[-1].assistant_message == result.assistant_message


@pytest.mark.asyncio
async def test_intermediate_brief_confirms_without_asking_advanced_ml_details() -> None:
    client = FakeLLMClient(
        [
            _complete_result(
                omit={"business_goal", "success_criteria", "forecast_type", "primary_metric"}
            )
        ]
    )
    engine, _, dialogue_id = await _start(client)

    result = await engine.handle_user_message(dialogue_id, MESSAGE)

    assert result.readiness.ready
    assert "confirm" in result.assistant_message.lower()
    assert "business_goal" not in result.assistant_message
    assert "success_criteria" not in result.assistant_message


@pytest.mark.asyncio
async def test_forecasting_language_promotes_ambiguous_initial_intent() -> None:
    initial = ExtractorResult(
        intent=Intent.AMBIGUOUS,
        intent_confidence=0.6,
        updates=[
            _update(
                "problem_statement",
                "Predict the inflation of Pakistan for the next 5 years",
                evidence="I want to predict the inflation of Pakistan over the next 5 years",
            ),
            _update("geography", "Pakistan", evidence="Pakistan"),
            _update("forecast_horizon", "5 years", evidence="next 5 years"),
        ],
    )
    client = FakeLLMClient(
        [initial],
        [QuestionOutput(question="How will the data be provided? Example answer: our data list.")],
    )
    engine, repository, dialogue_id = await _start(client)

    result = await engine.handle_user_message(
        dialogue_id, "I want to predict the inflation of Pakistan over the next 5 years"
    )

    state = repository.load_state(dialogue_id)
    assert state is not None
    assert state.intent == Intent.CREATE_FORECAST
    assert "time-series forecast" not in result.assistant_message


@pytest.mark.asyncio
async def test_catalog_answer_does_not_reopen_intent_question() -> None:
    initial = ExtractorResult(
        intent=Intent.AMBIGUOUS,
        intent_confidence=0.6,
        updates=[
            _update(
                "problem_statement",
                "Predict the inflation of Pakistan for the next 5 years",
                evidence="I want to predict the inflation of Pakistan over the next 5 years",
            ),
            _update("geography", "Pakistan", evidence="Pakistan"),
            _update("forecast_horizon", "5 years", evidence="next 5 years"),
        ],
    )
    client = FakeLLMClient(
        [initial, ExtractorResult(intent=Intent.AMBIGUOUS, intent_confidence=0.75)],
        [
            QuestionOutput(question="How will the data be provided? Example answer: our data list."),
            QuestionOutput(question="How often is a new observation recorded? Example answer: monthly."),
        ],
    )
    engine, repository, dialogue_id = await _start(client)

    await engine.handle_user_message(
        dialogue_id, "I want to predict the inflation of Pakistan over the next 5 years"
    )
    result = await engine.handle_user_message(dialogue_id, "our data list")

    state = repository.load_state(dialogue_id)
    assert state is not None
    assert state.intent == Intent.CREATE_FORECAST
    assert state.slots["source_mode"].value == "catalog"
    assert "time-series forecast" not in result.assistant_message


@pytest.mark.asyncio
async def test_yes_confirms_intermediate_brief_and_returns_specification() -> None:
    client = FakeLLMClient(
        [
            _complete_result(
                omit={"business_goal", "success_criteria", "forecast_type", "primary_metric"}
            )
        ]
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "yes")

    assert result.specification is not None
    assert result.assistant_message == "Confirmed. The forecasting requirements are complete."
    assert result.specification.deferred_slots


@pytest.mark.asyncio
async def test_pending_source_failure_preserves_first_turn_extraction() -> None:
    first = ExtractorResult(
        intent=Intent.CREATE_FORECAST,
        intent_confidence=0.9,
        updates=[
            _update("source_mode", "unmentioned", evidence="", status=SlotStatus.UNMENTIONED),
            _update(
                "problem_statement",
                "Predict inflation in Pakistan over the next 5 years",
                evidence="I want to predict the inflation in Pakistan over the next 5 years",
            ),
            _update("geography", "Pakistan", evidence="Pakistan"),
            _update("forecast_horizon", "5 years", evidence="5 years"),
        ],
    )

    class FirstThenConnectionFailure(FakeLLMClient):
        async def extract(self, message: str, state):
            if self.extractor_results:
                return await super().extract(message, state)
            raise LLMContractError("extractor provider request failed")

    client = FirstThenConnectionFailure(
        [first],
        [
            QuestionOutput(
                question="What does the target represent? Example answer: inflation rate."
            )
        ],
    )
    engine, repository, dialogue_id = await _start(client)

    await engine.handle_user_message(
        dialogue_id, "I want to predict the inflation in Pakistan over the next 5 years"
    )
    result = await engine.handle_user_message(dialogue_id, "our data list")

    state = repository.load_state(dialogue_id)
    assert state is not None
    assert state.intent == Intent.CREATE_FORECAST
    assert state.slots["geography"].value == ["Pakistan"]
    assert state.slots["forecast_horizon"].value == {"periods": 5.0, "unit": "year"}
    assert state.slots["source_mode"].value == "catalog"
    assert "intent" not in result.assistant_message.casefold()


@pytest.mark.asyncio
async def test_engine_trace_shows_answer_extraction_and_next_slot() -> None:
    traces: list[tuple[str, dict[str, object]]] = []
    repository = InMemoryDialogueRepository()
    client = FakeLLMClient([_complete_result(omit={"target_column"})], [
        QuestionOutput(question="Which column contains the value you want to predict? Example answer: revenue."),
    ])
    engine = ElicitationEngine(load_schema(), client, repository, trace_sink=lambda stage, payload: traces.append((stage, payload)))
    state = engine.start_dialogue()

    await engine.handle_user_message(state.dialogue_id, MESSAGE)

    stages = [stage for stage, _ in traces]
    assert stages[0] == "turn.user_message"
    assert "state.extraction_applied" in stages
    assert "state.next_slot" in stages
    assert stages[-1] == "turn.completed"
    next_slot = next(payload for stage, payload in traces if stage == "state.next_slot")
    assert next_slot["slot_id"] == "target_column"


@pytest.mark.asyncio
async def test_engine_persists_provider_conversation_id_from_persistent_client() -> None:
    class PersistentFakeLLMClient(FakeLLMClient):
        def __init__(self) -> None:
            super().__init__([_complete_result(omit={"target_column"})], [
                QuestionOutput(
                    question="Which column contains the value you want to predict? Example answer: revenue."
                )
            ])
            self.provider_conversation_id = "conv_test_123"

        def conversation_id_for(self, dialogue_id: UUID) -> str | None:
            return self.provider_conversation_id

    client = PersistentFakeLLMClient()
    repository = InMemoryDialogueRepository()
    engine = ElicitationEngine(load_schema(), client, repository)
    state = engine.start_dialogue()

    result = await engine.handle_user_message(state.dialogue_id, MESSAGE)

    assert result.state.provider_conversation_id == "conv_test_123"
    assert repository.load_state(state.dialogue_id).provider_conversation_id == "conv_test_123"


@pytest.mark.asyncio
async def test_missing_target_asks_exactly_one_target_question() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"target_column"})],
        [QuestionOutput(question="Which target column should be forecast? Example answer: revenue.")],
    )
    engine, _, dialogue_id = await _start(client)

    result = await engine.handle_user_message(dialogue_id, MESSAGE)

    assert not result.readiness.ready
    assert result.assistant_message == "Which target column should be forecast? Example answer: revenue."
    assert client.ask_requests[0].slot_id == "target_column"


@pytest.mark.asyncio
async def test_invalid_generated_question_retries_once_then_uses_valid_output() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"target_column"})],
        [
            QuestionOutput(question="What is the target? What is the horizon?"),
            QuestionOutput(question="Which target column should be forecast? Example answer: revenue."),
        ],
    )
    engine, _, dialogue_id = await _start(client)

    result = await engine.handle_user_message(dialogue_id, MESSAGE)

    assert result.assistant_message == "Which target column should be forecast? Example answer: revenue."
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
        [QuestionOutput(question="Which target column should be forecast? Example answer: revenue.")],
    )
    engine, _, dialogue_id = await _start(client)
    await engine.handle_user_message(dialogue_id, MESSAGE)

    result = await engine.handle_user_message(dialogue_id, "revenue")

    assert result.readiness.ready
    assert result.state.slots["target_column"].value == "revenue"


@pytest.mark.asyncio
async def test_short_answer_is_applied_to_the_slot_asked_by_the_previous_question() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"target_column"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [QuestionOutput(question="Which target column should be forecast? Example answer: revenue.")],
    )
    engine, _, dialogue_id = await _start(client)
    await engine.handle_user_message(dialogue_id, MESSAGE)

    result = await engine.handle_user_message(dialogue_id, "revenue")

    assert result.state.slots["target_column"].value == "revenue"
    assert result.state.slots["target_column"].status == SlotStatus.PROVIDED


@pytest.mark.asyncio
async def test_short_time_column_answer_follows_the_previous_question() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"target_column", "time_column"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(question="Which target column should be forecast? Example answer: revenue."),
            QuestionOutput(question="Which column contains the timestamps? Example answer: timestamp."),
        ],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    second = await engine.handle_user_message(dialogue_id, "revenue")
    result = await engine.handle_user_message(dialogue_id, "timestamp")

    assert first.assistant_message.startswith("Which target column")
    assert second.assistant_message.startswith("Which column contains the timestamps")
    assert result.state.slots["time_column"].value == "timestamp"
    assert result.state.slots["time_column"].status == SlotStatus.PROVIDED


@pytest.mark.asyncio
async def test_short_duration_answer_is_applied_to_the_pending_horizon_slot() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"forecast_horizon"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [QuestionOutput(question="How far ahead should we predict? Example answer: 7 days.")],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "7 days")

    assert first.assistant_message.startswith("How far ahead")
    assert result.state.slots["forecast_horizon"].value == {"periods": 7.0, "unit": "day"}
    assert result.state.slots["forecast_horizon"].status == SlotStatus.PROVIDED


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

    assert result.assistant_message == "How will the data be provided: upload a file, connect to an online service, use a database, or choose from our data list? Example answer: upload a file."
    assert result.state.slots == before.slots


@pytest.mark.asyncio
async def test_selected_enum_answer_recovers_when_extractor_fails() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"source_mode"})],
        [QuestionOutput(question="Will the data be uploaded, read from an API, read from a database, or selected from a catalog? Example answer: upload.")],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    assert first.assistant_message == (
        "Will the data be uploaded, read from an API, read from a database, or selected "
        "from a catalog? Example answer: upload."
    )

    result = await engine.handle_user_message(dialogue_id, "upload")

    assert result.state.slots["source_mode"].value == "upload"
    assert result.state.slots["source_mode"].status == SlotStatus.PROVIDED
    assert result.readiness.ready
    assert "confirm" in result.assistant_message.lower()


@pytest.mark.asyncio
async def test_data_list_phrase_fills_catalog_source_mode_on_first_try() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"source_mode"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(
                question="How will the data be provided? Example answer: upload a file."
            )
        ],
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "choose from your data list")

    assert result.state.slots["source_mode"].value == "catalog"
    assert result.state.slots["source_mode"].status == SlotStatus.PROVIDED
    assert "give a time span" not in result.assistant_message.casefold()


@pytest.mark.asyncio
async def test_clarification_question_does_not_repeat_invalid_duration_feedback() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"frequency"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(
                question="How often is a new observation recorded? Example answer: monthly."
            ),
            QuestionOutput(
                question="How often is a new observation recorded? Example answer: monthly."
            ),
        ],
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "time span for what")

    assert "How often is a new observation recorded?" in result.assistant_message
    assert "give a time span" not in result.assistant_message.casefold()


@pytest.mark.asyncio
async def test_frequency_feedback_explains_cadence_instead_of_forecast_horizon() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"frequency"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(
                question="How often is a new observation recorded? Example answer: monthly."
            )
        ],
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "not sure")

    assert "how often" in result.assistant_message.casefold()
    assert "time span" not in result.assistant_message.casefold()


@pytest.mark.asyncio
async def test_persistent_chat_can_answer_a_user_question_without_extracting_it() -> None:
    class ChatCapableFake(FakeLLMClient):
        def __init__(self) -> None:
            super().__init__(
                [_complete_result(omit={"frequency"})],
                [
                    QuestionOutput(
                        question="How often is a new observation recorded? Example answer: monthly."
                    )
                ],
            )
            self.chat_requests: list[str] = []

        async def answer_user_question(self, message: str, request) -> str:
            self.chat_requests.append(message)
            return (
                "It means how often your data gets a new value, such as every minute or day. "
                "How often is a new observation recorded? Example answer: once per minute."
            )

    client = ChatCapableFake()
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "What is a time span?")

    assert client.chat_requests == ["What is a time span?"]
    assert len(client.extract_requests) == 1
    assert "It means how often" in result.assistant_message
    assert result.state.slots["frequency"].status == SlotStatus.UNMENTIONED


@pytest.mark.asyncio
async def test_user_can_ask_what_a_question_means_without_an_extra_extraction_call() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"frequency"})],
        [
            QuestionOutput(
                question="How often is a new observation recorded? Example answer: monthly."
            )
        ],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "What do you mean by this question?")

    assert len(client.extract_requests) == 1
    assert result.state.slots["frequency"].status == SlotStatus.UNMENTIONED
    assert "how often a new data value is recorded" in result.assistant_message.casefold()
    assert "How often is a new observation recorded?" in result.assistant_message
    assert "Example answer:" in result.assistant_message
    assert result.assistant_message != first.assistant_message


@pytest.mark.asyncio
async def test_catalog_source_does_not_ask_dataset_schema_questions_before_selection() -> None:
    client = FakeLLMClient(
        [
            _complete_result(
                omit={
                    "source_mode",
                    "target_column",
                    "time_column",
                    "dataset_type",
                    "series_id_columns",
                    "hierarchy_columns",
                }
            ),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(
                question="How will the data be provided? Example answer: choose from our data list."
            ),
        ],
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "choose from our data list")

    assert [request.slot_id for request in client.ask_requests] == ["source_mode"]
    assert result.readiness.ready
    assert "confirm" in result.assistant_message.casefold()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        "our data list",
        "your data list",
        "our daat list",
        "from your data list",
        "please fetch it from the system data catalog",
    ],
)
async def test_data_list_variants_fill_catalog_source_mode_on_first_try(answer: str) -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"source_mode"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(
                question="How will the data be provided? Example answer: upload a file."
            )
        ],
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, answer)

    assert result.state.slots["source_mode"].value == "catalog"
    assert result.state.slots["source_mode"].status == SlotStatus.PROVIDED


@pytest.mark.asyncio
async def test_invalid_source_mode_answer_asks_for_confirmation_instead_of_repeating_choices() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"source_mode"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(
                question="How will the data be provided? Example answer: upload a file."
            )
        ],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    result = await engine.handle_user_message(dialogue_id, "no")

    assert result.assistant_message != first.assistant_message
    assert result.assistant_message.startswith("Did you mean")
    assert "catalog" in result.assistant_message.lower()
    assert "Example answer: yes." in result.assistant_message
    assert result.state.slots["source_mode"].value is None


@pytest.mark.asyncio
async def test_catalog_confirmation_is_accepted_as_source_mode() -> None:
    client = FakeLLMClient(
        [
            _complete_result(omit={"source_mode"}),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
            ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99),
        ],
        [
            QuestionOutput(
                question="How will the data be provided? Example answer: upload a file."
            )
        ],
    )
    engine, _, dialogue_id = await _start(client)

    await engine.handle_user_message(dialogue_id, MESSAGE)
    clarification = await engine.handle_user_message(dialogue_id, "I am not sure")
    assert clarification.assistant_message.startswith("Did you mean")

    result = await engine.handle_user_message(dialogue_id, "yes")

    assert result.state.slots["source_mode"].value == "catalog"
    assert result.state.slots["source_mode"].status == SlotStatus.PROVIDED


@pytest.mark.asyncio
async def test_selected_boolean_answer_recovers_when_extractor_fails() -> None:
    client = FakeLLMClient(
        [_complete_result(omit={"contains_sensitive_data"})],
        [
            QuestionOutput(
                question="Does the source contain personal, confidential, or regulated data? Example answer: yes."
            ),
            QuestionOutput(question="Which privacy or access restrictions apply? Example answer: internal users only."),
        ],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    assert first.assistant_message == "Does the source contain personal, confidential, or regulated data? Example answer: yes."

    result = await engine.handle_user_message(dialogue_id, "yes")

    assert result.state.slots["contains_sensitive_data"].value is True
    assert result.state.slots["contains_sensitive_data"].status == SlotStatus.PROVIDED
    assert "confirm" in result.assistant_message.lower()
    assert "privacy_constraints" in result.readiness.unresolved_slots


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
        [QuestionOutput(question="Does the source contain personal, confidential, or regulated data? Example answer: yes." )],
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
        [QuestionOutput(question="Do you want the system to create a time-series forecast? Example answer: yes.")],
    )
    engine, _, dialogue_id = await _start(client)

    first = await engine.handle_user_message(dialogue_id, MESSAGE)
    second = await engine.handle_user_message(dialogue_id, "yes")

    assert first.assistant_message == "Do you want the system to create a time-series forecast? Example answer: yes."
    assert second.state.intent == Intent.CREATE_FORECAST
    assert second.state.slots["intent"].value == Intent.CREATE_FORECAST.value
    assert second.state.slots["intent"].status == SlotStatus.PROVIDED
    assert second.assistant_message != "Do you want the system to create a time-series forecast? Example answer: yes."


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
