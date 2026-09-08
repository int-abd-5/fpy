from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, cast
from uuid import UUID

from openai import AsyncOpenAI

from forecasting_assistant.domain.models import (
    DialogueState,
    ExtractorResult,
    QuestionOutput,
    QuestionRequest,
)
from forecasting_assistant.domain.schema import ForecastingSchema
from forecasting_assistant.prompts.extractor import (
    build_extractor_input,
    build_extractor_instructions,
    safe_provider_value,
)
from forecasting_assistant.prompts.llmrei_long import (
    build_question_input,
    build_question_instructions,
)


class LLMContractError(RuntimeError):
    pass


TraceSink = Callable[[str, dict[str, Any]], None]


class OpenAIResponsesClient:
    _EXTRACTOR_MAX_OUTPUT_TOKENS = 1024
    _QUESTION_MAX_OUTPUT_TOKENS = 256
    _REQUEST_TIMEOUT_SECONDS = 20.0

    def __init__(
        self,
        api_key: str,
        model: str,
        schema: ForecastingSchema,
        *,
        client: AsyncOpenAI | None = None,
        trace_sink: TraceSink | None = None,
    ) -> None:
        self._client = (
            client
            if client is not None
            else AsyncOpenAI(
                api_key=api_key,
                max_retries=0,
                timeout=self._REQUEST_TIMEOUT_SECONDS,
            )
        )
        self._model = model
        self._schema = schema
        self._trace_sink = trace_sink

    async def _request_context(
        self, dialogue_id: UUID, saved_context_id: str | None
    ) -> dict[str, object]:
        """Return provider context options for one request.

        The default adapter deliberately does not retain provider-side state.
        The persistent pilot overrides this hook without changing the prompts.
        """
        return {"store": False}

    def _trace(self, stage: str, payload: dict[str, Any]) -> None:
        if self._trace_sink is None:
            return
        try:
            self._trace_sink(stage, safe_provider_value(payload))
        except Exception:  # noqa: BLE001 - tracing must never interrupt the API call
            return

    @staticmethod
    def _error_payload(error: Exception, elapsed_ms: float) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "elapsed_ms": round(elapsed_ms, 2),
        }
        request = getattr(error, "request", None)
        if request is not None:
            payload["request_method"] = getattr(request, "method", None)
            payload["request_url"] = str(getattr(request, "url", ""))

        current: BaseException = error
        for depth in range(1, 4):
            cause = current.__cause__ or current.__context__
            if cause is None:
                break
            payload[f"cause_{depth}_type"] = type(cause).__name__
            payload[f"cause_{depth}_message"] = str(cause)
            current = cause
        return payload

    def _latency_options(self) -> dict[str, object]:
        if self._model.casefold().startswith("gpt-5-mini"):
            return {"reasoning": {"effort": "minimal"}}
        return {}

    async def extract(self, message: str, state: DialogueState) -> ExtractorResult:
        started = perf_counter()
        try:
            parse = cast(Any, self._client.responses.parse)
            instructions = build_extractor_instructions()
            input_payload = build_extractor_input(message, state, self._schema)
            options = self._latency_options()
            context = await self._request_context(
                state.dialogue_id, state.provider_conversation_id
            )
            self._trace(
                "api.extract.request",
                {
                    "dialogue_id": str(state.dialogue_id),
                    "model": self._model,
                    "instructions": instructions,
                    "input": input_payload,
                    "max_output_tokens": self._EXTRACTOR_MAX_OUTPUT_TOKENS,
                    **context,
                    **options,
                },
            )
            response = await parse(
                model=self._model,
                instructions=instructions,
                input=input_payload,
                text_format=ExtractorResult,
                max_output_tokens=self._EXTRACTOR_MAX_OUTPUT_TOKENS,
                **context,
                **options,
            )
            parsed = cast(ExtractorResult | None, response.output_parsed)
            if parsed is None:
                raise LLMContractError("extractor returned no parsed output")
            response_payload = parsed.model_dump(mode="json")
            response_payload["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
            self._trace("api.extract.response", response_payload)
            return parsed
        except LLMContractError as error:
            self._trace("api.extract.failure", self._error_payload(error, (perf_counter() - started) * 1000))
            raise
        except Exception as error:
            self._trace("api.extract.failure", self._error_payload(error, (perf_counter() - started) * 1000))
            raise LLMContractError("extractor provider request failed") from error

    async def ask(self, request: QuestionRequest) -> QuestionOutput:
        started = perf_counter()
        try:
            parse = cast(Any, self._client.responses.parse)
            instructions = build_question_instructions()
            input_payload = build_question_input(request)
            options = self._latency_options()
            context = await self._request_context(
                request.dialogue_id or UUID(int=0), request.provider_conversation_id
            )
            self._trace(
                "api.question.request",
                {
                    "model": self._model,
                    "instructions": instructions,
                    "input": input_payload,
                    "max_output_tokens": self._QUESTION_MAX_OUTPUT_TOKENS,
                    **context,
                    **options,
                },
            )
            response = await parse(
                model=self._model,
                instructions=instructions,
                input=input_payload,
                text_format=QuestionOutput,
                max_output_tokens=self._QUESTION_MAX_OUTPUT_TOKENS,
                **context,
                **options,
            )
            parsed = cast(QuestionOutput | None, response.output_parsed)
            if parsed is None:
                raise LLMContractError("question generator returned no parsed output")
            response_payload = parsed.model_dump(mode="json")
            response_payload["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
            self._trace("api.question.response", response_payload)
            return parsed
        except LLMContractError as error:
            self._trace("api.question.failure", self._error_payload(error, (perf_counter() - started) * 1000))
            raise
        except Exception as error:
            self._trace("api.question.failure", self._error_payload(error, (perf_counter() - started) * 1000))
            raise LLMContractError("question provider request failed") from error


class PersistentOpenAIResponsesClient(OpenAIResponsesClient):
    """Pilot adapter that keeps one Responses conversation per dialogue.

    SQLite still owns the interview state. This adapter only gives the provider
    conversational context so its previous questions and answers are visible.
    """

    _CONVERSATION_MODE = "persistent_interview"
    _CHAT_MAX_OUTPUT_TOKENS = 300
    _CHAT_INSTRUCTIONS = (
        "Answer the user's follow-up question in simple, everyday language using the "
        "conversation context. Do not change or fill any forecasting requirement. Do not "
        "mention APIs, prompts, slots, schemas, or internal processing. After answering, "
        "repeat the current question and include one example answer so the user can continue."
    )

    def __init__(
        self,
        api_key: str,
        model: str,
        schema: ForecastingSchema,
        *,
        client: AsyncOpenAI | None = None,
        trace_sink: TraceSink | None = None,
    ) -> None:
        super().__init__(api_key, model, schema, client=client, trace_sink=trace_sink)
        self._conversation_ids: dict[UUID, str] = {}

    def conversation_id_for(self, dialogue_id: UUID) -> str | None:
        return self._conversation_ids.get(dialogue_id)

    async def _request_context(
        self, dialogue_id: UUID, saved_context_id: str | None
    ) -> dict[str, object]:
        conversation_id = saved_context_id or self._conversation_ids.get(dialogue_id)
        if conversation_id is None:
            conversations = getattr(self._client, "conversations", None)
            if conversations is None:
                raise LLMContractError(
                    "persistent interview requires an OpenAI client with conversations support"
                )
            conversation = await conversations.create(
                metadata={
                    "dialogue_id": str(dialogue_id),
                    "mode": self._CONVERSATION_MODE,
                }
            )
            conversation_id = str(getattr(conversation, "id", ""))
            if not conversation_id:
                raise LLMContractError("OpenAI returned no persistent conversation ID")
        self._conversation_ids[dialogue_id] = conversation_id
        return {"conversation": conversation_id, "store": True}

    async def answer_user_question(
        self, message: str, request: QuestionRequest
    ) -> str:
        started = perf_counter()
        try:
            create = cast(Any, self._client.responses.create)
            context = await self._request_context(
                request.dialogue_id or UUID(int=0),
                request.provider_conversation_id,
            )
            self._trace(
                "api.chat.request",
                {
                    "model": self._model,
                    "instructions": self._CHAT_INSTRUCTIONS,
                    "input": message,
                    "max_output_tokens": self._CHAT_MAX_OUTPUT_TOKENS,
                    **context,
                    **self._latency_options(),
                },
            )
            response = await create(
                model=self._model,
                instructions=self._CHAT_INSTRUCTIONS,
                input=message,
                max_output_tokens=self._CHAT_MAX_OUTPUT_TOKENS,
                **context,
                **self._latency_options(),
            )
            answer = str(getattr(response, "output_text", "")).strip()
            if not answer:
                raise LLMContractError("chat provider returned no text")
            self._trace(
                "api.chat.response",
                {
                    "answer": answer,
                    "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                },
            )
            return answer
        except LLMContractError as error:
            self._trace(
                "api.chat.failure",
                self._error_payload(error, (perf_counter() - started) * 1000),
            )
            raise
        except Exception as error:
            self._trace(
                "api.chat.failure",
                self._error_payload(error, (perf_counter() - started) * 1000),
            )
            raise LLMContractError("chat provider request failed") from error
