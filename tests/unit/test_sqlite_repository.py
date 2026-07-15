from pathlib import Path

import pytest

from forecasting_assistant.domain.models import DialogueTurn, ForecastingSpecification
from forecasting_assistant.domain.schema import create_initial_state, load_schema
from forecasting_assistant.infrastructure.persistence.sqlite_repository import (
    SQLiteDialogueRepository,
)


@pytest.fixture
def repository(tmp_path: Path) -> SQLiteDialogueRepository:
    result = SQLiteDialogueRepository(tmp_path / "elicitation.db")
    result.initialize()
    return result


def test_state_round_trip_preserves_schema_and_turns(
    repository: SQLiteDialogueRepository,
) -> None:
    state = create_initial_state(load_schema())
    state.turns.append(DialogueTurn(turn_number=1, user_message="forecast monthly sales"))

    repository.save_state(state)
    loaded = repository.load_state(state.dialogue_id)

    assert loaded == state
    assert loaded.schema_version == "1.0.0"


def test_events_are_append_only_and_round_trip(repository: SQLiteDialogueRepository) -> None:
    state = create_initial_state(load_schema())
    repository.save_state(state)

    repository.append_event(state.dialogue_id, "first", {"value": 1})
    repository.append_event(state.dialogue_id, "second", {"value": 2})

    assert repository.list_events(state.dialogue_id) == [
        {"event_type": "first", "payload": {"value": 1}},
        {"event_type": "second", "payload": {"value": 2}},
    ]


def test_specification_round_trip(repository: SQLiteDialogueRepository) -> None:
    state = create_initial_state(load_schema())
    repository.save_state(state)
    specification = ForecastingSpecification(
        dialogue_id=state.dialogue_id,
        schema_version="1.0.0",
        values={"target_column": "revenue"},
        user_provided_slots=["target_column"],
        confirmed_inferred_slots=[],
        documented_defaults={"backtest_folds": 3},
        unresolved_optional_slots=[],
    )

    repository.save_specification(specification)

    assert repository.load_specification(state.dialogue_id) == specification


@pytest.mark.parametrize(
    "secret",
    [
        "sk-supersecret123",
        "api_key=supersecret",
        "password=hunter2",
        "Bearer bearer-secret",
        "X-Amz-Signature=signature-secret",
    ],
)
def test_redacts_secret_material_before_state_and_event_persistence(
    repository: SQLiteDialogueRepository, secret: str
) -> None:
    state = create_initial_state(load_schema())
    state.turns.append(DialogueTurn(turn_number=1, user_message=f"Use {secret}"))

    repository.save_state(state)
    repository.append_event(state.dialogue_id, "user_message", {"message": secret})

    loaded = repository.load_state(state.dialogue_id)
    events = repository.list_events(state.dialogue_id)
    assert secret not in loaded.model_dump_json()
    assert secret not in str(events)
    assert "[REDACTED]" in loaded.turns[0].user_message


def test_preserves_external_secret_reference(repository: SQLiteDialogueRepository) -> None:
    state = create_initial_state(load_schema())
    state.slots["authentication_reference"].value = "secret://warehouse-readonly"

    repository.save_state(state)

    loaded = repository.load_state(state.dialogue_id)
    assert loaded.slots["authentication_reference"].value == "secret://warehouse-readonly"


def test_does_not_preserve_secret_reference_with_embedded_query_credential(
    repository: SQLiteDialogueRepository,
) -> None:
    state = create_initial_state(load_schema())
    unsafe = "secret://warehouse?password=hunter2"
    state.turns.append(DialogueTurn(turn_number=1, user_message=unsafe))

    repository.save_state(state)

    assert unsafe not in repository.load_state(state.dialogue_id).model_dump_json()
