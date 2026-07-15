from typing import Protocol

from forecasting_assistant.domain.models import (
    DialogueState,
    ExtractorResult,
    QuestionOutput,
    QuestionRequest,
)


class StructuredLLMClient(Protocol):
    async def extract(self, message: str, state: DialogueState) -> ExtractorResult:
        raise NotImplementedError

    async def ask(self, request: QuestionRequest) -> QuestionOutput:
        raise NotImplementedError
