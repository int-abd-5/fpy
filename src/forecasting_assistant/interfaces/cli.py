from __future__ import annotations

import asyncio
import json
from uuid import UUID

import typer

from forecasting_assistant.application.orchestrator import ElicitationEngine
from forecasting_assistant.config import get_settings
from forecasting_assistant.domain.schema import load_schema
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
            return

        result = asyncio.run(engine.handle_user_message(state.dialogue_id, message))
        state = result.state
        typer.echo(result.assistant_message)
