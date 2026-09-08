from __future__ import annotations

from dataclasses import dataclass

from forecasting_assistant.domain.conditions import is_slot_active
from forecasting_assistant.domain.models import DialogueState, Intent
from forecasting_assistant.domain.schema import ForecastingSchema, SlotDefinition


@dataclass(frozen=True)
class OntologyPath:
    aspect: str
    dimension: str


_ASPECT_LABELS = {
    "request": "forecast objective",
    "target": "forecast target",
    "time": "time structure",
    "series": "series structure",
    "source": "data source",
    "history": "historical coverage",
    "quality": "data quality",
    "seasonality": "seasonality",
    "covariates": "additional signals",
    "output": "forecast output",
    "evaluation": "evaluation",
    "operations": "operations",
    "governance": "governance",
}

_DIMENSION_LABELS = {
    "intent": "forecast purpose",
    "problem_statement": "what to predict",
    "source_mode": "source choice",
    "source_reference": "source selection",
    "target_column": "target field",
    "target_description": "target meaning",
    "time_column": "time field",
    "frequency": "observation frequency",
    "forecast_horizon": "forecast horizon",
    "dataset_type": "series organization",
    "geography": "geographic scope",
    "forecast_type": "prediction format",
    "output_granularity": "result grouping",
}

_ASPECT_KEYWORDS = {
    "request": ("want", "need", "predict", "forecast", "estimate"),
    "target": ("target", "predict", "forecast", "value", "rate", "price", "sales", "inflation"),
    "time": ("when", "often", "daily", "weekly", "monthly", "year", "month", "date", "future", "next"),
    "series": ("country", "region", "store", "product", "group", "hierarch", "separate"),
    "source": ("data", "file", "upload", "catalog", "database", "online", "service"),
    "output": ("result", "value", "range", "uncertainty", "report", "api"),
}


def ontology_path(definition: SlotDefinition) -> OntologyPath:
    return OntologyPath(
        aspect=_ASPECT_LABELS.get(definition.area, definition.area),
        dimension=_DIMENSION_LABELS.get(definition.slot_id, definition.description),
    )


def gate_pruned_slots(schema: ForecastingSchema, state: DialogueState) -> frozenset[str]:
    """Return slots that the current interview state has closed or deactivated."""
    pruned = {
        definition.slot_id
        for definition in schema.slots
        if not is_slot_active(definition, state)
    }
    if state.intent == Intent.CREATE_FORECAST:
        pruned.add("intent")
    return frozenset(pruned)


def relevance_bonus(definition: SlotDefinition, state: DialogueState) -> int:
    """Apply a small local ScoreOnto/ReRankOnto-style relevance bonus."""
    if not state.turns:
        return 0
    keywords = _ASPECT_KEYWORDS.get(definition.area, ())
    message = state.turns[-1].user_message.casefold()
    return min(30, sum(5 for keyword in keywords if keyword in message)) if keywords else 0
