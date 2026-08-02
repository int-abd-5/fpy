from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from forecasting_assistant.domain.datasets import (
    DatasetCandidate,
    DatasetSearchQuery,
    DatasetSelection,
    DatasetVersion,
    FetchResult,
    SourcePlan,
)


class HttpClient(Protocol):
    def get_bytes(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResult:
        raise NotImplementedError

    def get_json(self, url: str, *, headers: dict[str, str] | None = None) -> Any:
        raise NotImplementedError


class DatasetSourceAdapter(Protocol):
    source_id: str

    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]:
        raise NotImplementedError

    def describe(self, candidate_id: str) -> DatasetCandidate:
        raise NotImplementedError

    def fetch(self, candidate: DatasetCandidate) -> FetchResult:
        raise NotImplementedError


class DatasetCatalogRepository(Protocol):
    def initialize(self) -> None:
        raise NotImplementedError

    def save_candidate(self, candidate: DatasetCandidate) -> None:
        raise NotImplementedError

    def load_candidate(self, candidate_id: str) -> DatasetCandidate | None:
        raise NotImplementedError

    def save_plan(self, plan: SourcePlan) -> None:
        raise NotImplementedError

    def load_plan(self, plan_id: UUID) -> SourcePlan | None:
        raise NotImplementedError

    def save_selection(self, selection: DatasetSelection) -> None:
        raise NotImplementedError

    def load_selection(self, selection_id: UUID) -> DatasetSelection | None:
        raise NotImplementedError

    def save_version(self, version: DatasetVersion) -> None:
        raise NotImplementedError

    def load_version(self, version_id: UUID) -> DatasetVersion | None:
        raise NotImplementedError

    def find_cached_version(
        self, cache_key: str, *, user_id: str | None
    ) -> DatasetVersion | None:
        raise NotImplementedError
