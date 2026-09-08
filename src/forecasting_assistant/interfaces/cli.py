from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

import typer

from forecasting_assistant.application.dataset_discovery import DatasetDiscoveryService
from forecasting_assistant.application.orchestrator import ElicitationEngine
from forecasting_assistant.config import get_settings
from forecasting_assistant.domain.datasets import CatalogClass, SourcePlan
from forecasting_assistant.domain.models import ForecastingSpecification, Intent
from forecasting_assistant.domain.schema import create_initial_state, load_schema
from forecasting_assistant.infrastructure.datasets.http import SecureHttpClient
from forecasting_assistant.infrastructure.datasets.object_store import ContentAddressedObjectStore
from forecasting_assistant.infrastructure.datasets.registry import build_default_adapters
from forecasting_assistant.infrastructure.datasets.sqlite_repository import (
    SQLiteDatasetCatalogRepository,
)
from forecasting_assistant.infrastructure.llm.openai_responses import (
    OpenAIResponsesClient,
    PersistentOpenAIResponsesClient,
)
from forecasting_assistant.infrastructure.observability.pipeline_logger import JsonlPipelineLogger
from forecasting_assistant.infrastructure.persistence.sqlite_repository import (
    SQLiteDialogueRepository,
)

app = typer.Typer(help="Forecasting requirement elicitation tools.")


@app.callback()
def main() -> None:
    """Run forecasting requirement elicitation commands."""


def _emit_trace(stage: str, payload: dict[str, Any]) -> None:
    typer.echo(
        f"[trace] {stage} {json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)}",
        err=True,
    )


def _compose_trace_sinks(
    *sinks: Callable[[str, dict[str, Any]], None] | None,
) -> Callable[[str, dict[str, Any]], None]:
    active_sinks = [sink for sink in sinks if sink is not None]

    def emit(stage: str, payload: dict[str, Any]) -> None:
        for sink in active_sinks:
            sink(stage, payload)

    return emit


def build_engine(
    *,
    trace_sink: Callable[[str, dict[str, Any]], None] | None = None,
    persistent: bool = False,
) -> ElicitationEngine:
    settings = get_settings()
    if not settings.openai_api_key:
        raise typer.BadParameter("OPENAI_API_KEY is required for the LLM interview command")
    schema = load_schema(settings.schema_version)
    pipeline_sink = JsonlPipelineLogger(settings.elicitation_log_path)
    combined_sink = _compose_trace_sinks(pipeline_sink, trace_sink)
    repository = SQLiteDialogueRepository(settings.elicitation_db_path)
    repository.initialize()
    provider_class = PersistentOpenAIResponsesClient if persistent else OpenAIResponsesClient
    provider = provider_class(
        settings.openai_api_key,
        settings.openai_model,
        schema,
        trace_sink=combined_sink,
    )
    return ElicitationEngine(schema, provider, repository, trace_sink=combined_sink)


def _world_bank_demo_values() -> dict[str, object]:
    return {
        "intent": Intent.CREATE_FORECAST.value,
        "problem_statement": "Forecast Pakistan annual consumer price inflation from trusted public data.",
        "business_goal": "macroeconomic monitoring",
        "success_criteria": "low MAE on annual inflation backtests",
        "target_column": "FP.CPI.TOTL.ZG",
        "target_description": "Pakistan annual consumer price inflation",
        "target_unit": "percent",
        "time_column": "date",
        "frequency": {"periods": 1, "unit": "year"},
        "forecast_horizon": {"periods": 3, "unit": "year"},
        "dataset_type": "single_series",
        "geography": ["Pakistan"],
        "source_mode": "catalog",
        "source_reference": "world-bank:PK:FP.CPI.TOTL.ZG",
        "source_provider": "World Bank",
        "forecast_type": "point",
        "output_granularity": "annual",
        "primary_metric": "mae",
        "minimum_training_points": 30,
        "contains_sensitive_data": False,
        "license": "CC BY 4.0",
    }


def build_dataset_service() -> tuple[DatasetDiscoveryService, SQLiteDialogueRepository]:
    settings = get_settings()
    dialogue_repository = SQLiteDialogueRepository(settings.elicitation_db_path)
    dialogue_repository.initialize()
    catalog_repository = SQLiteDatasetCatalogRepository(settings.elicitation_db_path)
    catalog_repository.initialize()
    http = SecureHttpClient()
    service = DatasetDiscoveryService(
        build_default_adapters(http),
        catalog_repository,
        ContentAddressedObjectStore(settings.dataset_store_path),
    )
    return service, dialogue_repository


@app.command("seed-world-bank-demo")
def seed_world_bank_demo(
    db_path: str = typer.Option(
        "elicitation.db",
        "--db-path",
        help="SQLite database path where the confirmed demo specification is saved.",
    ),
    schema_version: str = typer.Option(
        "1.0.0",
        "--schema-version",
        help="Forecasting schema version to stamp on the demo specification.",
    ),
) -> None:
    """Create a confirmed trusted-source demo specification for World Bank inflation data."""
    schema = load_schema(schema_version)
    repository = SQLiteDialogueRepository(db_path)
    repository.initialize()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    repository.save_state(state)
    values = _world_bank_demo_values()
    specification = ForecastingSpecification(
        dialogue_id=state.dialogue_id,
        schema_version=schema_version,
        values=values,
        user_provided_slots=list(values),
        confirmed_inferred_slots=[],
        documented_defaults={},
        unresolved_optional_slots=[],
    )
    repository.save_specification(specification)
    typer.echo("Created confirmed trusted-source World Bank demo specification.")
    typer.echo(str(state.dialogue_id))


def _render_source_plan(plan: SourcePlan) -> str:
    payload = {
        "plan_id": str(plan.plan_id),
        "recommendations": [
            {
                "candidate_id": item.candidate.candidate_id,
                "title": item.candidate.title,
                "publisher": item.candidate.publisher,
                "score": item.ranking.total,
                "score_breakdown": item.ranking.model_dump(mode="json"),
                "source_url": item.candidate.source_url,
                "frequency": item.candidate.frequency,
                "temporal_start": item.candidate.temporal_start,
                "temporal_end": item.candidate.temporal_end,
                "license": item.candidate.license.model_dump(mode="json"),
                "acquisition_mode": item.candidate.acquisition_mode,
                "limitations": item.ranking.limitations,
            }
            for item in plan.recommendations
        ],
        "unavailable_alternatives": [
            {
                "title": item.candidate.title,
                "publisher": item.candidate.publisher,
                "reasons": item.ranking.rejection_reasons,
            }
            for item in plan.unavailable_alternatives
        ],
        "source_errors": plan.source_errors,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)


async def _run_interview(
    engine: ElicitationEngine,
    dialogue_id: str | None,
    *,
    persistent: bool = False,
) -> None:
    if dialogue_id is None:
        state = engine.start_dialogue()
    else:
        try:
            state = engine.get_state(UUID(dialogue_id))
        except (ValueError, KeyError) as error:
            raise typer.BadParameter("dialogue ID was not found or is invalid") from error

    typer.echo("Describe the time-series forecast you need.")
    while True:
        try:
            message = typer.prompt("You").strip()
        except (EOFError, typer.Abort):
            typer.echo("Interview ended.")
            return

        command = message.lower()
        if command == "/quit":
            typer.echo("Interview ended.")
            return
        if command == "/show":
            state = engine.get_state(state.dialogue_id)
            typer.echo(state.model_dump_json(indent=2))
            continue
        if command == "/confirm":
            try:
                specification = engine.confirm_specification(
                    state.dialogue_id, confirm=True
                )
            except ValueError as error:
                typer.echo(f"Cannot confirm: {error}")
                continue
            typer.echo(
                json.dumps(
                    specification.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            service, _ = build_dataset_service()
            plan = service.discover_for_specification(specification)
            typer.echo("Dataset recommendations (explicit selection is still required):")
            typer.echo(_render_source_plan(plan))
            return

        result = await engine.handle_user_message(state.dialogue_id, message)
        state = result.state
        typer.echo(result.assistant_message)
        if result.specification is not None:
            if result.specification.values.get("source_mode") == "catalog":
                service, _ = build_dataset_service()
                plan = service.discover_for_specification(result.specification)
                typer.echo("Dataset recommendations (explicit selection is still required):")
                typer.echo(_render_source_plan(plan))
            return


@app.command()
def interview(
    dialogue_id: str | None = typer.Option(
        None, "--dialogue-id", help="Resume an existing dialogue UUID."
    ),
    trace: bool = typer.Option(
        False,
        "--trace",
        help="Print sanitized API requests, responses, and state transitions.",
    ),
) -> None:
    """Run an interactive forecasting requirements interview."""
    engine = build_engine(trace_sink=_emit_trace) if trace else build_engine()
    asyncio.run(_run_interview(engine, dialogue_id))


@app.command("persistent-interview")
def persistent_interview(
    dialogue_id: str | None = typer.Option(
        None, "--dialogue-id", help="Resume an existing dialogue UUID."
    ),
    trace: bool = typer.Option(
        False,
        "--trace",
        help="Compatibility flag; persistent mode keeps diagnostics in the log file.",
    ),
) -> None:
    """Run the pilot interview with one persistent provider conversation."""
    del trace
    engine = build_engine(persistent=True)
    asyncio.run(_run_interview(engine, dialogue_id, persistent=True))


@app.command("discover-datasets")
def discover_datasets(
    dialogue_id: str = typer.Argument(..., help="Confirmed dialogue UUID."),
    user_id: str | None = typer.Option(None, "--user-id", help="User scope for private data."),
    research: bool = typer.Option(
        False, "--research", help="Search the benchmark/research catalog instead."
    ),
) -> None:
    """Rank up to three datasets for a confirmed forecasting specification."""
    try:
        parsed_id = UUID(dialogue_id)
    except ValueError as error:
        raise typer.BadParameter("dialogue ID is invalid") from error
    service, dialogue_repository = build_dataset_service()
    specification = dialogue_repository.load_specification(parsed_id)
    if specification is None:
        raise typer.BadParameter("dialogue has no confirmed forecasting specification")
    purpose = CatalogClass.RESEARCH if research else CatalogClass.PRODUCTION
    plan = service.discover_for_specification(specification, user_id=user_id, purpose=purpose)
    typer.echo(_render_source_plan(plan))


@app.command("confirm-dataset")
def confirm_dataset(
    plan_id: str = typer.Argument(..., help="Dataset source-plan UUID."),
    candidate_id: str = typer.Argument(..., help="Eligible recommended candidate ID."),
    user_id: str | None = typer.Option(None, "--user-id", help="User scope for private data."),
) -> None:
    """Explicitly confirm one of the plan's eligible recommendations."""
    service, _ = build_dataset_service()
    try:
        selection = service.confirm_dataset(
            UUID(plan_id), candidate_id, confirm=True, user_id=user_id
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(selection.model_dump_json(indent=2))


@app.command("fetch-dataset")
def fetch_dataset(
    selection_id: str = typer.Argument(..., help="Confirmed dataset-selection UUID."),
) -> None:
    """Fetch a confirmed dataset, reusing a permitted fresh cached version."""
    service, _ = build_dataset_service()
    try:
        version = service.fetch_selection(UUID(selection_id))
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(version.model_dump_json(indent=2))


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Host for the local web UI."),
    port: int = typer.Option(8765, "--port", help="Port for the local web UI."),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open the browser automatically."),
) -> None:
    """Run the local web demo interface."""
    from forecasting_assistant.interfaces.web import run_web_server

    run_web_server(host=host, port=port, open_browser=open_browser)
