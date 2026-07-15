from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from forecasting_assistant.domain.schema import SlotDefinition


def _items(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [item.strip() for item in str(value).split(",")]


def normalize_value(definition: SlotDefinition, value: Any) -> Any:
    value_type = definition.value_type
    if value is None:
        return None
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
        result = []
        for item in _items(value):
            try:
                result.append(float(item))
            except (TypeError, ValueError):
                result.append(item)
        return result
    if value_type in {"integer_list", "enum_list"}:
        result = []
        for item in _items(value):
            try:
                result.append(int(item)) if value_type == "integer_list" else result.append(str(item).strip().lower())
            except (TypeError, ValueError):
                result.append(item)
        return result
    if value_type in {"string_list", "privacy_constraints"}:
        return [str(item).strip() for item in _items(value)]
    if value_type == "duration" and isinstance(value, dict):
        result = dict(value)
        try:
            result["periods"] = int(result["periods"])
        except (KeyError, TypeError, ValueError):
            pass
        if "unit" in result:
            result["unit"] = str(result["unit"]).strip().lower()
        return result
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
