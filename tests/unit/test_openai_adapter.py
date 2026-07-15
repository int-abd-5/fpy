from types import SimpleNamespace

import pytest

from forecasting_assistant.domain.models import ExtractorResult, Intent
from forecasting_assistant.domain.schema import create_initial_state, load_schema
from forecasting_assistant.infrastructure.llm.openai_responses import (
    LLMContractError,
    OpenAIResponsesClient,
)
from tests.fakes import FakeLLMClient


class RecordingResponses:
    def __init__(self, parsed: ExtractorResult | None) -> None:
        self.parsed = parsed
        self.kwargs: dict[str, object] | None = None

    async def parse(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.parsed)


class InjectedClient:
    def __init__(self, responses: RecordingResponses) -> None:
        self.responses = responses


class RaisingResponses:
    async def parse(self, **kwargs: object) -> SimpleNamespace:
        raise TimeoutError("provider timed out")


def _result() -> ExtractorResult:
    return ExtractorResult(intent=Intent.CREATE_FORECAST, intent_confidence=0.99)


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
async def test_fake_client_queues_results_and_records_requests() -> None:
    expected = _result()
    fake = FakeLLMClient([expected])
    state = create_initial_state(load_schema())

    assert await fake.extract("message", state) == expected
    assert fake.extract_requests == [("message", state)]
