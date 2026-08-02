from __future__ import annotations

import asyncio
import json
from uuid import UUID

import typer

from forecasting_assistant.application.dataset_discovery import DatasetDiscoveryService
from forecasting_assistant.application.orchestrator import ElicitationEngine
from forecasting_assistant.config import get_settings
from forecasting_assistant.domain.datasets import CatalogClass, SourcePlan
from forecasting_assistant.domain.schema import load_schema
from forecasting_assistant.infrastructure.datasets.http import SecureHttpClient
from forecasting_assistant.infrastructure.datasets.object_store import ContentAddressedObjectStore
from forecasting_assistant.infrastructure.datasets.registry import build_default_adapters
from forecasting_assistant.infrastructure.datasets.sqlite_repository import (
    SQLiteDatasetCatalogRepository,
)
from forecasting_assistant.infrastructure.llm.openai_responses import OpenAIResponsesClient
from forecasting_assistant.infrastructure.persistence.sqlite_repository import (
    SQLiteDialogueRepository,
)

app = typer.Typer(help="Forecasting requirement elicitation tools.")


@app.callback()
def main() -> None:
    """Run forecasting requirement elicitation commands."""


def build_engine() -> ElicitationEngine:
    settings = get_settings()
    schema = load_schema(settings.schema_version)
    repository = SQLiteDialogueRepository(settings.elicitation_db_path)
    repository.initialize()
    provider = OpenAIResponsesClient(
        settings.openai_api_key,
        settings.openai_model,
        schema,
    )
    return ElicitationEngine(schema, provider, repository)


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


@app.command()
def interview(
    dialogue_id: str | None = typer.Option(
        None, "--dialogue-id", help="Resume an existing dialogue UUID."
    ),
) -> None:
    """Run an interactive forecasting requirements interview."""
    engine = build_engine()
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

        result = asyncio.run(engine.handle_user_message(state.dialogue_id, message))
        state = result.state
        typer.echo(result.assistant_message)


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
