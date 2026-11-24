from __future__ import annotations

from datetime import date
from typing import Any

from forecasting_assistant.domain.datasets import CatalogClass, DatasetSearchQuery
from forecasting_assistant.domain.models import ForecastingSpecification


def _duration_text(value: Any) -> str | None:
    if isinstance(value, dict) and (value.get("unit") or value.get("units")):
        unit = str(value.get("unit") or value["units"])
        periods = value.get("periods", 1)
        unit = {
            "seconds": "second",
            "minutes": "minute",
            "hours": "hour",
            "days": "day",
            "weeks": "week",
            "months": "month",
            "quarters": "quarter",
            "years": "year",
        }.get(unit.casefold(), unit.casefold())
        aliases = {
            "hour": "hourly",
            "day": "daily",
            "week": "weekly",
            "month": "monthly",
            "quarter": "quarterly",
            "year": "annual",
        }
        return aliases.get(unit.casefold(), f"every {periods} {unit}")
    return str(value) if value else None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("text", "value", "label", "name"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return None
    if value is None:
        return None
    return str(value).strip() or None


def _date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def query_from_specification(
    specification: ForecastingSpecification,
    *,
    user_id: str | None = None,
    purpose: CatalogClass = CatalogClass.PRODUCTION,
) -> DatasetSearchQuery:
    values = specification.values
    target_parts = [
        values.get("target_description"),
        values.get("target_column"),
        values.get("problem_statement"),
        values.get("business_goal"),
    ]
    target = " ".join(
        text for value in target_parts if (text := _text_value(value)) is not None
    ).strip()
    if not target:
        raise ValueError("confirmed specification does not define a forecast target")
    prompt_parts = [
        values.get("problem_statement"),
        values.get("target_description"),
        values.get("business_goal"),
    ]
    prompt = " ".join(
        text for value in prompt_parts if (text := _text_value(value)) is not None
    ).strip() or target
    return DatasetSearchQuery(
        target=target,
        prompt=prompt,
        geography=_string_list(values.get("geography")),
        frequency=_duration_text(values.get("frequency")),
        history_start=_date(values.get("history_start")),
        history_end=_date(values.get("history_end")),
        minimum_training_points=int(values.get("minimum_training_points", 30)),
        purpose=purpose,
        source_mode=str(values.get("source_mode")) if values.get("source_mode") else None,
        source_reference=(
            str(values.get("source_reference")) if values.get("source_reference") else None
        ),
        license_hint=str(values.get("license")) if values.get("license") else None,
        contains_sensitive_data=bool(values.get("contains_sensitive_data", False)),
        user_id=user_id,
    )
