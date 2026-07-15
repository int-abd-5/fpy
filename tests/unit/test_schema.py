from forecasting_assistant.domain.models import Requiredness, SlotStatus
from forecasting_assistant.domain.schema import create_initial_state, load_schema


def test_schema_has_unique_ids_and_approved_version() -> None:
    schema = load_schema()
    slot_ids = [slot.slot_id for slot in schema.slots]

    assert schema.version == "1.0.0"
    assert len(slot_ids) == len(set(slot_ids))
    assert {"target_column", "frequency", "forecast_horizon", "source_mode"} <= set(slot_ids)


def test_initial_state_contains_every_slot_as_unmentioned() -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    assert set(state.slots) == {slot.slot_id for slot in schema.slots}
    assert all(slot.status == SlotStatus.UNMENTIONED for slot in state.slots.values())
    assert schema.get("intent").requiredness == Requiredness.REQUIRED
