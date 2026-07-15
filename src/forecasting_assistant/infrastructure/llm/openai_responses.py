from __future__ import annotations

from openai import AsyncOpenAI

from forecasting_assistant.domain.models import DialogueState, ExtractorResult
from forecasting_assistant.domain.schema import ForecastingSchema
from forecasting_assistant.prompts.extractor import (
    build_extractor_input,
    build_extractor_instructions,
)


class LLMContractError(RuntimeError):
    pass


class OpenAIResponsesClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        schema: ForecastingSchema,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._client = client if client is not None else AsyncOpenAI(api_key=api_key)
        self._model = model
        self._schema = schema

    async def extract(self, message: str, state: DialogueState) -> ExtractorResult:
        response = await self._client.responses.parse(
            model=self._model,
            instructions=build_extractor_instructions(),
            input=build_extractor_input(message, state, self._schema),
            text_format=ExtractorResult,
            store=False,
        )
        if response.output_parsed is None:
            raise LLMContractError("extractor returned no parsed output")
        return response.output_parsed
