from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

from forecasting_assistant.domain.datasets import (
    DatasetCandidate,
    DatasetSelection,
    DatasetVersion,
    SourcePlan,
)


class SQLiteDatasetCatalogRepository:
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
                CREATE TABLE IF NOT EXISTS dataset_candidates (
                  candidate_id TEXT PRIMARY KEY,
                  adapter_id TEXT NOT NULL,
                  catalog_class TEXT NOT NULL,
                  candidate_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dataset_source_plans (
                  plan_id TEXT PRIMARY KEY,
                  specification_id TEXT NOT NULL,
                  plan_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dataset_selections (
                  selection_id TEXT PRIMARY KEY,
                  plan_id TEXT NOT NULL,
                  specification_id TEXT NOT NULL,
                  candidate_id TEXT NOT NULL,
                  selection_json TEXT NOT NULL,
                  confirmed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dataset_versions (
                  version_id TEXT PRIMARY KEY,
                  candidate_id TEXT NOT NULL,
                  cache_key TEXT NOT NULL,
                  user_id TEXT,
                  shared INTEGER NOT NULL,
                  version_json TEXT NOT NULL,
                  retrieved_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_dataset_versions_cache
                  ON dataset_versions(cache_key, user_id, retrieved_at);
                """
            )

    def save_candidate(self, candidate: DatasetCandidate) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dataset_candidates(
                  candidate_id, adapter_id, catalog_class, candidate_json, updated_at
                ) VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(candidate_id) DO UPDATE SET
                  adapter_id = excluded.adapter_id,
                  catalog_class = excluded.catalog_class,
                  candidate_json = excluded.candidate_json,
                  updated_at = excluded.updated_at
                """,
                (
                    candidate.candidate_id,
                    candidate.adapter_id,
                    candidate.catalog_class.value,
                    candidate.model_dump_json(),
                ),
            )

    def load_candidate(self, candidate_id: str) -> DatasetCandidate | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT candidate_json FROM dataset_candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
        return None if row is None else DatasetCandidate.model_validate_json(row["candidate_json"])

    def save_plan(self, plan: SourcePlan) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dataset_source_plans(plan_id, specification_id, plan_json, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(plan_id) DO UPDATE SET plan_json = excluded.plan_json
                """,
                (
                    str(plan.plan_id),
                    str(plan.specification_id),
                    plan.model_dump_json(),
                    plan.created_at.isoformat(),
                ),
            )

    def load_plan(self, plan_id: UUID) -> SourcePlan | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT plan_json FROM dataset_source_plans WHERE plan_id = ?",
                (str(plan_id),),
            ).fetchone()
        return None if row is None else SourcePlan.model_validate_json(row["plan_json"])

    def save_selection(self, selection: DatasetSelection) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dataset_selections(
                  selection_id, plan_id, specification_id, candidate_id,
                  selection_json, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(selection_id) DO UPDATE SET
                  selection_json = excluded.selection_json,
                  confirmed_at = excluded.confirmed_at
                """,
                (
                    str(selection.selection_id),
                    str(selection.plan_id),
                    str(selection.specification_id),
                    selection.candidate_id,
                    selection.model_dump_json(),
                    selection.confirmed_at.isoformat(),
                ),
            )

    def load_selection(self, selection_id: UUID) -> DatasetSelection | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT selection_json FROM dataset_selections WHERE selection_id = ?",
                (str(selection_id),),
            ).fetchone()
        return None if row is None else DatasetSelection.model_validate_json(row["selection_json"])

    def save_version(self, version: DatasetVersion) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dataset_versions(
                  version_id, candidate_id, cache_key, user_id, shared,
                  version_json, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(version.version_id),
                    version.candidate_id,
                    version.cache_key,
                    version.user_id,
                    int(version.shared),
                    version.model_dump_json(),
                    version.retrieved_at.isoformat(),
                ),
            )

    def load_version(self, version_id: UUID) -> DatasetVersion | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT version_json FROM dataset_versions WHERE version_id = ?",
                (str(version_id),),
            ).fetchone()
        return None if row is None else DatasetVersion.model_validate_json(row["version_json"])

    def find_cached_version(
        self, cache_key: str, *, user_id: str | None
    ) -> DatasetVersion | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT version_json
                FROM dataset_versions
                WHERE cache_key = ? AND (shared = 1 OR user_id = ?)
                ORDER BY retrieved_at DESC
                LIMIT 1
                """,
                (cache_key, user_id),
            ).fetchone()
        return None if row is None else DatasetVersion.model_validate_json(row["version_json"])
