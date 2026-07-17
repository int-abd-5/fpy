from datetime import datetime
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from forecasting_assistant.domain.schema import SlotDefinition


_DURATION_UNITS = {
    "second": "second",
    "seconds": "second",
    "secondly": "second",
    "minute": "minute",
    "minutes": "minute",
    "minutely": "minute",
    "hour": "hour",
    "hours": "hour",
    "hourly": "hour",
    "day": "day",
    "days": "day",
    "daily": "day",
    "week": "week",
    "weeks": "week",
    "weekly": "week",
    "month": "month",
    "months": "month",
    "monthly": "month",
    "quarter": "quarter",
    "quarters": "quarter",
    "quarterly": "quarter",
    "year": "year",
    "years": "year",
    "yearly": "year",
}
_DURATION_TEXT_PATTERN = re.compile(
    r"\s*(?:(?:for|over)\s+)?(?:(?:the\s+)?(?:next|following)\s+)?"
    r"(?:(?P<number>\d+(?:\.\d+)?)|(?:a|an|one))?\s*(?P<unit>[a-zA-Z]+)\s*",
    re.IGNORECASE,
)


def _items(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [item.strip() for item in str(value).split(",")]


def _duration_from_text(value: str) -> dict[str, Any] | None:
    match = _DURATION_TEXT_PATTERN.fullmatch(value)
    if match is None:
        return None
    unit = _DURATION_UNITS.get(match.group("unit").lower())
    if unit is None:
        return None
    return {"periods": float(match.group("number") or 1), "unit": unit}


def normalize_value(definition: SlotDefinition, value: Any) -> Any:
    value_type = definition.value_type
    if value is None:
        return None
    if value_type in {"percentage_list", "probability_list", "integer_list", "enum_list", "string_list", "privacy_constraints"} and isinstance(value, dict):
        return value
    if value_type in {"enum", "timezone"}:
        return str(value).strip().lower() if value_type == "enum" else str(value).strip()
    if value_type == "boolean":
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in {"true", "yes", "y", "1"}:
            return True
        if str(value).strip().lower() in {"false", "no", "n", "0"}:
            return False
        return value
    if value_type in {"percentage", "probability"}:
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if value_type in {"percentage_list", "probability_list"}:
        numeric_items: list[Any] = []
        for item in _items(value):
            try:
                numeric_items.append(float(item))
            except (TypeError, ValueError):
                numeric_items.append(item)
        return numeric_items
    if value_type in {"integer_list", "enum_list"}:
        normalized_items: list[Any] = []
        for item in _items(value):
            try:
                normalized_items.append(int(item)) if value_type == "integer_list" else normalized_items.append(str(item).strip().lower())
            except (TypeError, ValueError):
                normalized_items.append(item)
        return normalized_items
    if value_type in {"string_list", "privacy_constraints"}:
        return [str(item).strip() for item in _items(value)]
    if value_type == "duration":
        if isinstance(value, str):
            return _duration_from_text(value) or value
        if isinstance(value, dict):
            duration = dict(value)
            try:
                duration["periods"] = float(duration["periods"])
            except (KeyError, TypeError, ValueError):
                pass
            if "unit" in duration:
                duration["unit"] = str(duration["unit"]).strip().lower()
            return duration
    if value_type == "datetime" and isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value


def is_iana_timezone(value: Any) -> bool:
    if not isinstance(value, str) or not value or value.upper() in {"UTC", "GMT"}:
        return value in {"UTC", "GMT"}
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return "/" in value
