from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from copy import deepcopy
from typing import Any
from uuid import UUID

from forecasting_assistant.domain.models import (
    DialogueState,
    ExtractorResult,
    QuestionOutput,
    QuestionRequest,
    ForecastingSpecification,
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


class InMemoryDialogueRepository:
    def __init__(self) -> None:
        self.states: dict[UUID, DialogueState] = {}
        self.events: list[tuple[UUID, str, dict[str, Any]]] = []
        self.specifications: dict[UUID, ForecastingSpecification] = {}

    def load_state(self, dialogue_id: UUID) -> DialogueState | None:
        state = self.states.get(dialogue_id)
        return None if state is None else state.model_copy(deep=True)

    def save_state(self, state: DialogueState) -> None:
        self.states[state.dialogue_id] = state.model_copy(deep=True)

    def append_event(
        self, dialogue_id: UUID, event_type: str, payload: dict[str, Any]
    ) -> None:
        self.events.append((dialogue_id, event_type, deepcopy(payload)))

    def save_specification(self, specification: ForecastingSpecification) -> None:
        self.specifications[specification.dialogue_id] = specification.model_copy(deep=True)
