from uuid import uuid4

from forecasting_assistant.config import Settings
from forecasting_assistant.domain.datasets import DatasetSearchQuery, SourcePlan
from forecasting_assistant.domain.models import SlotStatus
from forecasting_assistant.domain.schema import create_initial_state, load_schema
from forecasting_assistant.infrastructure.llm.openai_responses import (
    PersistentOpenAIResponsesClient,
)
from forecasting_assistant.interfaces import web
from forecasting_assistant.interfaces.web import (
    _extract_uploaded_columns,
    _source_plan_payload,
    _state_payload,
    dashboard_html,
)


def test_dashboard_html_exposes_demo_panels() -> None:
    html = dashboard_html()

    assert "Forecast Studio" in html
    assert "Upload data" in html
    assert "Data catalog" in html
    assert "Fetch dataset" in html
    assert "/api/dialogues" in html
    assert "sessionStorage" in html
    assert "[trace]" not in html
    assert "Events" not in html


def test_uploaded_csv_columns_are_available_for_dataset_questions() -> None:
    columns = _extract_uploaded_columns("sales.csv", b"date,region,revenue\n2026-01-01,PK,10\n")

    assert columns == ["date", "region", "revenue"]


def test_uploaded_json_columns_are_available_for_dataset_questions() -> None:
    columns = _extract_uploaded_columns("sales.json", b'[{"date":"2026-01-01","revenue":10}]')

    assert columns == ["date", "revenue"]


def test_dashboard_server_uses_persistent_provider(monkeypatch, tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        openai_model="test-model",
        elicitation_db_path=str(tmp_path / "dialogue.db"),
        dataset_store_path=str(tmp_path / "datasets"),
        elicitation_log_path=str(tmp_path / "logs" / "pipeline.jsonl"),
    )
    monkeypatch.setattr(web, "get_settings", lambda: settings)

    server = web.DashboardServer("127.0.0.1", 0)
    try:
        assert isinstance(server.engine._llm, PersistentOpenAIResponsesClient)
    finally:
        server.server.server_close()


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
