from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError
from openai.lib._pydantic import to_strict_json_schema

from forecasting_assistant.domain.models import (
    ExtractorResult,
    Intent,
    QuestionOutput,
    QuestionRequest,
    SlotState,
)
from forecasting_assistant.domain.schema import create_initial_state, load_schema
from forecasting_assistant.infrastructure.llm import openai_responses
from forecasting_assistant.infrastructure.llm.openai_responses import (
    LLMContractError,
    OpenAIResponsesClient,
    PersistentOpenAIResponsesClient,
)
from tests.fakes import FakeLLMClient


class RecordingResponses:
    def __init__(self, parsed: ExtractorResult | QuestionOutput | None) -> None:
        self.parsed = parsed
        self.kwargs: dict[str, object] | None = None

    async def parse(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.parsed)


class RecordingChatResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.kwargs: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(output_text=self.output_text)


class InjectedClient:
    def __init__(self, responses: RecordingResponses) -> None:
        self.responses = responses


class RecordingConversations:
    def __init__(self, conversation_id: str = "conv_pilot_123") -> None:
        self.conversation_id = conversation_id
        self.create_calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.create_calls.append(kwargs)
        return SimpleNamespace(id=self.conversation_id)


class PersistentInjectedClient(InjectedClient):
    def __init__(self, responses: RecordingResponses) -> None:
        super().__init__(responses)
        self.conversations = RecordingConversations()


class PersistentChatInjectedClient:
    def __init__(self, responses: RecordingChatResponses) -> None:
        self.responses = responses
        self.conversations = RecordingConversations()


class RaisingResponses:
    async def parse(self, **kwargs: object) -> SimpleNamespace:
        raise TimeoutError("provider timed out")


class RaisingConnectionResponses:
    async def parse(self, **kwargs: object) -> SimpleNamespace:
        request = httpx.Request("POST", "https://api.openai.com/v1/responses")
        try:
            raise OSError("temporary DNS failure")
        except OSError as error:
            raise APIConnectionError(request=request) from error


class RecordingOpenAI:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


def test_adapter_configures_low_latency_provider_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Provider(RecordingOpenAI):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.update(kwargs)

    monkeypatch.setattr(openai_responses, "AsyncOpenAI", Provider)

    OpenAIResponsesClient("unused-key", "configured-model", load_schema())

    assert captured["max_retries"] == 0
    assert captured["timeout"] == 20.0


@pytest.mark.asyncio
async def test_adapter_uses_minimal_reasoning_for_gpt5_mini() -> None:
    responses = RecordingResponses(_result())
    adapter = OpenAIResponsesClient(
        "unused-key", "gpt-5-mini-2025-08-07", load_schema(), client=InjectedClient(responses)
    )

    await adapter.extract("I need a forecast.", create_initial_state(load_schema()))

    assert responses.kwargs is not None
    assert responses.kwargs["reasoning"] == {"effort": "minimal"}


@pytest.mark.asyncio
async def test_adapter_does_not_send_gpt5_reasoning_options_to_other_models() -> None:
    responses = RecordingResponses(_result())
    adapter = OpenAIResponsesClient(
        "unused-key", "gpt-4.1-mini", load_schema(), client=InjectedClient(responses)
    )

    await adapter.extract("I need a forecast.", create_initial_state(load_schema()))

    assert responses.kwargs is not None
    assert "reasoning" not in responses.kwargs


@pytest.mark.asyncio
async def test_adapter_emits_redacted_request_and_response_trace() -> None:
    responses = RecordingResponses(_result())
    traces: list[tuple[str, dict[str, object]]] = []
    adapter = OpenAIResponsesClient(
        "unused-key",
        "configured-model",
        load_schema(),
        client=InjectedClient(responses),
        trace_sink=lambda stage, payload: traces.append((stage, payload)),
    )

    await adapter.extract("api_key=super-secret", create_initial_state(load_schema()))

    stages = [stage for stage, _ in traces]
    serialized = str(traces)
    assert stages == ["api.extract.request", "api.extract.response"]
    assert "super-secret" not in serialized
    assert traces[1][1]["updates"] == []


def _result() -> ExtractorResult:
    return ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99)


def _question_request() -> QuestionRequest:
    return QuestionRequest(
        slot_id="frequency",
        reason="missing required slot",
        slot_description="Native observation frequency.",
        current_state=SlotState(slot_id="frequency"),
        confirmed_context={"target_description": "sales"},
        static_question="How often are sales observed?",
    )


def test_extractor_candidate_value_has_a_typed_strict_schema() -> None:
    schema = to_strict_json_schema(ExtractorResult)
    candidate_schema = schema["$defs"]["SlotUpdate"]["properties"]["candidate_value"]

    assert "type" in candidate_schema


@pytest.mark.asyncio
async def test_adapter_uses_configured_structured_request_without_network() -> None:
    responses = RecordingResponses(_result())
    client = InjectedClient(responses)
    adapter = OpenAIResponsesClient("unused-key", "configured-model", load_schema(), client=client)

    result = await adapter.extract("I need a forecast.", create_initial_state(load_schema()))

    assert result == _result()
    assert responses.kwargs is not None
    assert responses.kwargs["model"] == "configured-model"
    assert responses.kwargs["text_format"] is ExtractorResult
    assert responses.kwargs["max_output_tokens"] == 1024
    assert responses.kwargs["store"] is False
    assert "conversation" not in responses.kwargs


@pytest.mark.asyncio
async def test_adapter_rejects_missing_parsed_output() -> None:
    responses = RecordingResponses(None)
    adapter = OpenAIResponsesClient("unused-key", "configured-model", load_schema(), client=InjectedClient(responses))

    with pytest.raises(LLMContractError, match="extractor returned no parsed output"):
        await adapter.extract("I need a forecast.", create_initial_state(load_schema()))


@pytest.mark.asyncio
async def test_adapter_wraps_provider_exception_with_chaining() -> None:
    client = InjectedClient(RaisingResponses())
    adapter = OpenAIResponsesClient("unused-key", "configured-model", load_schema(), client=client)

    with pytest.raises(LLMContractError, match="extractor provider request failed") as error:
        await adapter.extract("I need a forecast.", create_initial_state(load_schema()))

    assert isinstance(error.value.__cause__, TimeoutError)


@pytest.mark.asyncio
async def test_adapter_trace_includes_underlying_connection_cause() -> None:
    traces: list[tuple[str, dict[str, object]]] = []
    adapter = OpenAIResponsesClient(
        "unused-key",
        "configured-model",
        load_schema(),
        client=InjectedClient(RaisingConnectionResponses()),
        trace_sink=lambda stage, payload: traces.append((stage, payload)),
    )

    with pytest.raises(LLMContractError):
        await adapter.extract("I need a forecast.", create_initial_state(load_schema()))

    failure = next(payload for stage, payload in traces if stage == "api.extract.failure")
    assert failure["error_type"] == "APIConnectionError"
    assert failure["cause_1_type"] == "OSError"
    assert failure["cause_1_message"] == "temporary DNS failure"
    assert failure["request_url"] == "https://api.openai.com/v1/responses"


@pytest.mark.asyncio
async def test_question_adapter_uses_structured_stateless_request() -> None:
    expected = QuestionOutput(question="How often are sales observed?")
    responses = RecordingResponses(expected)
    adapter = OpenAIResponsesClient(
        "unused-key", "configured-model", load_schema(), client=InjectedClient(responses)
    )

    assert await adapter.ask(_question_request()) == expected
    assert responses.kwargs is not None
    assert responses.kwargs["model"] == "configured-model"
    assert responses.kwargs["text_format"] is QuestionOutput
    assert responses.kwargs["max_output_tokens"] == 256
    assert responses.kwargs["store"] is False
    assert "conversation" not in responses.kwargs


@pytest.mark.asyncio
async def test_persistent_adapter_reuses_one_provider_conversation_for_a_dialogue() -> None:
    responses = RecordingResponses(_result())
    client = PersistentInjectedClient(responses)
    adapter = PersistentOpenAIResponsesClient(
        "unused-key", "configured-model", load_schema(), client=client
    )
    state = create_initial_state(load_schema())

    await adapter.extract("I need a forecast.", state)
    request = _question_request().model_copy(
        update={"dialogue_id": state.dialogue_id, "provider_conversation_id": "conv_pilot_123"}
    )
    await adapter.ask(request)

    assert len(client.conversations.create_calls) == 1
    assert client.conversations.create_calls[0]["metadata"] == {
        "dialogue_id": str(state.dialogue_id),
        "mode": "persistent_interview",
    }
    assert responses.kwargs is not None
    assert responses.kwargs["conversation"] == "conv_pilot_123"
    assert responses.kwargs["store"] is True
    assert "previous_response_id" not in responses.kwargs


@pytest.mark.asyncio
async def test_persistent_adapter_uses_saved_conversation_without_creating_another() -> None:
    responses = RecordingResponses(_result())
    client = PersistentInjectedClient(responses)
    adapter = PersistentOpenAIResponsesClient(
        "unused-key", "configured-model", load_schema(), client=client
    )
    state = create_initial_state(load_schema())
    state.provider_conversation_id = "conv_saved_456"

    await adapter.extract("continue", state)

    assert client.conversations.create_calls == []
    assert responses.kwargs is not None
    assert responses.kwargs["conversation"] == "conv_saved_456"


@pytest.mark.asyncio
async def test_persistent_adapter_answers_user_questions_in_the_same_conversation() -> None:
    responses = RecordingChatResponses(
        "It asks how often a new value is recorded. How often is data recorded?"
    )
    client = PersistentChatInjectedClient(responses)
    adapter = PersistentOpenAIResponsesClient(
        "unused-key", "configured-model", load_schema(), client=client
    )
    state = create_initial_state(load_schema())
    request = _question_request().model_copy(
        update={"dialogue_id": state.dialogue_id, "provider_conversation_id": "conv_pilot_123"}
    )

    answer = await adapter.answer_user_question("What does this question mean?", request)

    assert answer.startswith("It asks how often")
    assert client.conversations.create_calls == []
    assert responses.kwargs is not None
    assert responses.kwargs["conversation"] == "conv_pilot_123"
    assert responses.kwargs["store"] is True


@pytest.mark.asyncio
async def test_question_adapter_rejects_missing_parsed_output() -> None:
    responses = RecordingResponses(None)
    adapter = OpenAIResponsesClient(
        "unused-key", "configured-model", load_schema(), client=InjectedClient(responses)
    )

    with pytest.raises(LLMContractError, match="question generator returned no parsed output"):
        await adapter.ask(_question_request())


@pytest.mark.asyncio
async def test_question_adapter_wraps_provider_exception() -> None:
    adapter = OpenAIResponsesClient(
        "unused-key", "configured-model", load_schema(), client=InjectedClient(RaisingResponses())
    )

    with pytest.raises(LLMContractError, match="question provider request failed") as error:
        await adapter.ask(_question_request())

    assert isinstance(error.value.__cause__, TimeoutError)


@pytest.mark.asyncio
async def test_fake_client_queues_results_and_records_requests() -> None:
    expected = _result()
    fake = FakeLLMClient([expected])
    state = create_initial_state(load_schema())

    assert await fake.extract("message", state) == expected
    assert fake.extract_requests == [("message", state)]
