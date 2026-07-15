from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from forecasting_assistant.domain.models import (
    DialogueState,
    ExtractorResult,
    QuestionOutput,
    QuestionRequest,
)


class FakeLLMClient:
    def __init__(
        self,
        extractor_results: Iterable[ExtractorResult] = (),
        question_results: Iterable[QuestionOutput] = (),
    ) -> None:
        self.extractor_results = deque(extractor_results)
        self.question_results = deque(question_results)
        self.extract_requests: list[tuple[str, DialogueState]] = []
        self.ask_requests: list[QuestionRequest] = []

    async def extract(self, message: str, state: DialogueState) -> ExtractorResult:
        self.extract_requests.append((message, state))
        if not self.extractor_results:
            raise AssertionError("fake extractor queue is empty")
        return self.extractor_results.popleft()

    async def ask(self, request: QuestionRequest) -> QuestionOutput:
        self.ask_requests.append(request)
        if not self.question_results:
            raise AssertionError("fake question queue is empty")
        return self.question_results.popleft()
