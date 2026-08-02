from uuid import uuid4

from forecasting_assistant.domain.datasets import DatasetSearchQuery, SourcePlan
from forecasting_assistant.domain.models import SlotStatus
from forecasting_assistant.domain.schema import create_initial_state, load_schema
from forecasting_assistant.interfaces.web import (
    _source_plan_payload,
    _state_payload,
    dashboard_html,
)


def test_dashboard_html_exposes_demo_panels() -> None:
    html = dashboard_html()

    assert "Forecast Requirement Elicitation" in html
    assert "Saved Specs" in html
    assert "Datasets" in html
    assert "Slots" in html
    assert "/api/dialogues" in html


def test_state_payload_lists_slots_for_viewer() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.slots["target_column"].value = "btc_usd_close"
    state.slots["target_column"].status = SlotStatus.PROVIDED
    state.slots["target_column"].evidence_text = "btc_usd_close"

    payload = _state_payload(state)

    target = next(slot for slot in payload["slots"] if slot["slot_id"] == "target_column")
    assert target["value"] == "btc_usd_close"
    assert target["status"] == "provided"


def test_source_plan_payload_is_json_ready() -> None:
    plan = SourcePlan(
        specification_id=uuid4(),
        query=DatasetSearchQuery(target="temperature"),
    )

    payload = _source_plan_payload(plan)

    assert payload["plan_id"] == str(plan.plan_id)
    assert payload["query"]["target"] == "temperature"
