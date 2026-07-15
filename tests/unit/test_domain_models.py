import pytest
from pydantic import ValidationError

from forecasting_assistant.domain.models import SlotState, SlotStatus, SlotUpdate


def test_provided_slot_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        SlotState(slot_id="frequency", value="daily", status=SlotStatus.PROVIDED)


def test_update_rejects_unknown_confidence_range() -> None:
    with pytest.raises(ValidationError):
        SlotUpdate(
            slot_id="frequency",
            candidate_value="daily",
            status=SlotStatus.PROVIDED,
            confidence=1.2,
            evidence_text="daily sales",
        )
