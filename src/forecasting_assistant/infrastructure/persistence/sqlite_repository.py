from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from forecasting_assistant.domain.models import DialogueState, ForecastingSpecification
from forecasting_assistant.prompts.extractor import safe_provider_value


class SQLiteDialogueRepository:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS dialogues (
                  dialogue_id TEXT PRIMARY KEY,
                  schema_version TEXT NOT NULL,
                  state_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  dialogue_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS specifications (
                  specification_id TEXT PRIMARY KEY,
                  dialogue_id TEXT NOT NULL UNIQUE,
                  specification_json TEXT NOT NULL,
                  confirmed_at TEXT NOT NULL
                );
                """
            )

    def _dump(self, value: BaseModel | dict[str, Any]) -> str:
        raw = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        sanitized = safe_provider_value(raw)
        return json.dumps(sanitized, ensure_ascii=False, sort_keys=True)

    def save_state(self, state: DialogueState) -> None:
        payload = self._dump(state)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dialogues(dialogue_id, schema_version, state_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(dialogue_id) DO UPDATE SET
                  schema_version = excluded.schema_version,
                  state_json = excluded.state_json,
                  updated_at = excluded.updated_at
                """,
                (
                    str(state.dialogue_id),
                    state.schema_version,
                    payload,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def load_state(self, dialogue_id: UUID) -> DialogueState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM dialogues WHERE dialogue_id = ?",
                (str(dialogue_id),),
            ).fetchone()
        return None if row is None else DialogueState.model_validate_json(row["state_json"])

    def append_event(
        self, dialogue_id: UUID, event_type: str, payload: dict[str, Any]
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO events(dialogue_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(dialogue_id),
                    event_type,
                    self._dump(payload),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_events(self, dialogue_id: UUID) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_type, payload_json
                FROM events
                WHERE dialogue_id = ?
                ORDER BY event_id
                """,
                (str(dialogue_id),),
            ).fetchall()
        return [
            {"event_type": row["event_type"], "payload": json.loads(row["payload_json"])}
            for row in rows
        ]

    def save_specification(self, specification: ForecastingSpecification) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO specifications(
                  specification_id, dialogue_id, specification_json, confirmed_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(dialogue_id) DO UPDATE SET
                  specification_id = excluded.specification_id,
                  specification_json = excluded.specification_json,
                  confirmed_at = excluded.confirmed_at
                """,
                (
                    str(specification.specification_id),
                    str(specification.dialogue_id),
                    self._dump(specification),
                    specification.confirmed_at.isoformat(),
                ),
            )

    def load_specification(
        self, dialogue_id: UUID
    ) -> ForecastingSpecification | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT specification_json FROM specifications WHERE dialogue_id = ?",
                (str(dialogue_id),),
            ).fetchone()
        if row is None:
            return None
        return ForecastingSpecification.model_validate_json(row["specification_json"])

