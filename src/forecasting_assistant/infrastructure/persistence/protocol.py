from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from forecasting_assistant.domain.models import DialogueState, ForecastingSpecification


class DialogueRepository(Protocol):
    def load_state(self, dialogue_id: UUID) -> DialogueState | None:
        raise NotImplementedError

    def save_state(self, state: DialogueState) -> None:
        raise NotImplementedError

    def append_event(
        self, dialogue_id: UUID, event_type: str, payload: dict[str, Any]
    ) -> None:
        raise NotImplementedError

    def save_specification(self, specification: ForecastingSpecification) -> None:
        raise NotImplementedError
