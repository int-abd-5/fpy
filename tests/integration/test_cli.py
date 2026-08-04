from uuid import UUID

from typer.testing import CliRunner

from forecasting_assistant.config import get_settings
from forecasting_assistant.domain.models import (
    ForecastingSpecification,
    Intent,
    ReadinessReport,
    TurnResult,
)
from forecasting_assistant.infrastructure.persistence.sqlite_repository import SQLiteDialogueRepository
from forecasting_assistant.domain.schema import create_initial_state, load_schema
from forecasting_assistant.interfaces import cli


class FakeEngine:
    def __init__(self) -> None:
        self.state = create_initial_state(load_schema())
        self.state.intent = Intent.CREATE_FORECAST
        self.messages: list[str] = []

    def start_dialogue(self):
        return self.state.model_copy(deep=True)

    def get_state(self, dialogue_id: UUID):
        assert dialogue_id == self.state.dialogue_id
        return self.state.model_copy(deep=True)

    async def handle_user_message(self, dialogue_id: UUID, message: str) -> TurnResult:
        assert dialogue_id == self.state.dialogue_id
        self.messages.append(message)
        readiness = ReadinessReport(
            ready=True,
            active_required_slots=[],
            unresolved_slots=[],
            issues=[],
        )
        return TurnResult(
            state=self.state.model_copy(deep=True),
            assistant_message="Please confirm the monthly sales specification.",
            readiness=readiness,
        )

    def confirm_specification(
        self, dialogue_id: UUID, *, confirm: bool
    ) -> ForecastingSpecification:
        assert confirm is True
        return ForecastingSpecification(
            dialogue_id=dialogue_id,
            schema_version="1.0.0",
            values={"target_column": "revenue"},
            user_provided_slots=["target_column"],
            confirmed_inferred_slots=[],
            documented_defaults={},
            unresolved_optional_slots=[],
        )


def test_interview_prints_one_message_per_turn_and_final_json(monkeypatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr(cli, "build_engine", lambda: engine)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["interview"],
        input=(
            "Forecast monthly sales for the next year using sales.xlsx.\n"
            "/confirm\n"
        ),
    )

    assert result.exit_code == 0
    assert result.output.count("Please confirm the monthly sales specification.") == 1
    assert '"target_column": "revenue"' in result.output
    assert "unused-key" not in result.output
    assert engine.messages == ["Forecast monthly sales for the next year using sales.xlsx."]


def test_show_and_quit_do_not_call_provider(monkeypatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr(cli, "build_engine", lambda: engine)

    result = CliRunner().invoke(cli.app, ["interview"], input="/show\n/quit\n")

    assert result.exit_code == 0
    assert str(engine.state.dialogue_id) in result.output
    assert engine.messages == []


def test_seed_world_bank_demo_creates_confirmed_trusted_source_spec(tmp_path) -> None:
    db_path = tmp_path / "demo.db"
    result = CliRunner().invoke(
        cli.app,
        ["seed-world-bank-demo", "--db-path", str(db_path)],
    )

    assert result.exit_code == 0
    dialogue_id = UUID(result.output.strip().splitlines()[-1])
    specification = SQLiteDialogueRepository(db_path).load_specification(dialogue_id)

    assert specification is not None
    assert specification.values["source_mode"] == "catalog"
    assert specification.values["source_reference"] == "world-bank:PK:FP.CPI.TOTL.ZG"
    assert specification.values["target_description"] == "Pakistan annual consumer price inflation"


def test_dataset_service_does_not_require_openai_key(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("ELICITATION_DB_PATH", str(tmp_path / "demo.db"))
    monkeypatch.setenv("DATASET_STORE_PATH", str(tmp_path / "dataset_store"))
    get_settings.cache_clear()

    try:
        cli.build_dataset_service()
    finally:
        get_settings.cache_clear()
