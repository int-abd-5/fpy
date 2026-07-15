import re
from datetime import datetime
from typing import Any

from forecasting_assistant.application.normalization import is_iana_timezone, normalize_value
from forecasting_assistant.domain.conditions import is_slot_active
from forecasting_assistant.domain.models import DialogueState, ValidationIssue
from forecasting_assistant.domain.schema import ForecastingSchema, SlotDefinition


_CREDENTIAL_PATTERN = re.compile(r"(?:sk-[A-Za-z0-9]|(?:api[_-]?key|token|password)\s*=|Bearer\s+)", re.I)


def _issue(slot_id: str | None, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(slot_id=slot_id, code=code, message=message)


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def validate_slot(definition: SlotDefinition, state) -> list[ValidationIssue]:
    value = normalize_value(definition, state.value)
    issues: list[ValidationIssue] = []
    if value is None:
        return issues
    if definition.allowed_values and definition.value_type == "enum" and value not in definition.allowed_values:
        issues.append(_issue(definition.slot_id, "unsupported_value", f"Value must be one of {definition.allowed_values}."))
    if definition.value_type in {"percentage", "percentage_list"}:
        values = value if isinstance(value, list) else [value]
        if any(_number(item) is None or not 0 <= _number(item) <= 100 for item in values):
            issues.append(_issue(definition.slot_id, "percentage_range", "Percentage must be between 0 and 100."))
    if definition.value_type == "probability_list":
        if any(_number(item) is None or not 0 <= _number(item) <= 1 for item in value):
            issues.append(_issue(definition.slot_id, "probability_range", "Probability must be between 0 and 1."))
    if definition.value_type == "duration":
        periods = value.get("periods") if isinstance(value, dict) else None
        if _number(periods) is None or _number(periods) <= 0:
            issues.append(_issue(definition.slot_id, "positive_duration", "Duration periods must be positive."))
    if definition.value_type == "timezone" and not is_iana_timezone(value):
        issues.append(_issue(definition.slot_id, "iana_timezone", "Value must be an IANA timezone."))
    if definition.value_type == "secret_reference" and (not isinstance(value, str) or not value.startswith("secret://")):
        issues.append(_issue(definition.slot_id, "secret_reference", "Credential values must use a secret:// reference."))
    if isinstance(value, str) and _CREDENTIAL_PATTERN.search(value):
        issues.append(_issue(definition.slot_id, "raw_credential", "Raw credentials are not accepted."))
    return issues


def validate_dialogue(schema: ForecastingSchema, state: DialogueState) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for definition in schema.slots:
        slot_state = state.slots[definition.slot_id]
        if is_slot_active(definition, state):
            issues.extend(validate_slot(definition, slot_state))

    def value(slot_id: str) -> Any:
        return state.slots[slot_id].value

    history_start, history_end = _datetime(value("history_start")), _datetime(value("history_end"))
    if history_start and history_end and history_start >= history_end:
        issues.append(_issue("history_start", "history_order", "history_start must be earlier than history_end."))
    forecast_start, cutoff = _datetime(value("forecast_start")), _datetime(value("data_cutoff"))
    if forecast_start and cutoff and forecast_start < cutoff:
        issues.append(_issue("forecast_start", "forecast_start_after_cutoff", "forecast_start must not precede data_cutoff."))
    dataset_type = value("dataset_type")
    if dataset_type in {"panel", "hierarchical"} and not value("series_id_columns"):
        issues.append(_issue("series_id_columns", "series_id_columns_required", "Panel and hierarchical datasets require series identifiers."))
    if dataset_type == "hierarchical" and not value("hierarchy_columns"):
        issues.append(_issue("hierarchy_columns", "hierarchy_columns_required", "Hierarchical datasets require hierarchy columns."))
    if value("forecast_type") in {"probabilistic", "both"} and not (value("prediction_interval_levels") or value("quantiles")):
        issues.append(_issue("forecast_type", "probabilistic_output_required", "Probabilistic output requires intervals or quantiles."))
    if value("known_future_covariates") and not value("covariate_availability"):
        issues.append(_issue("covariate_availability", "covariate_availability_required", "Future covariates require availability information."))
    return issues
