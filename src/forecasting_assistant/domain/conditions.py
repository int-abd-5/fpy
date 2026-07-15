from collections.abc import Callable

from forecasting_assistant.domain.models import DialogueState, SlotStatus
from forecasting_assistant.domain.schema import SlotDefinition


def _value(state: DialogueState, slot_id: str) -> object:
    return state.slots[slot_id].value


def _mentioned(state: DialogueState, slot_id: str) -> bool:
    return state.slots[slot_id].status != SlotStatus.UNMENTIONED


def _duration_unit(state: DialogueState, slot_id: str) -> str | None:
    value = _value(state, slot_id)
    if isinstance(value, dict) and value.get("unit") is not None:
        return str(value["unit"]).lower()
    return None


def _source_reference(state: DialogueState) -> str:
    value = _value(state, "source_reference")
    return str(value).lower() if value is not None else ""


def _selected_covariates(state: DialogueState) -> list[str]:
    selected: list[str] = []
    for slot_id in ("past_covariates", "known_future_covariates"):
        value = _value(state, slot_id)
        if isinstance(value, list):
            selected.extend(str(item) for item in value)
    return selected


def _target_requires_sign_rule(state: DialogueState) -> bool:
    bounds = _value(state, "target_bounds")
    minimum = bounds.get("minimum") if isinstance(bounds, dict) else None
    try:
        return minimum is not None and float(minimum) < 0
    except (TypeError, ValueError):
        return False


RULES: dict[str, Callable[[DialogueState], bool]] = {
    "target_requires_sign_rule": _target_requires_sign_rule,
    "granularity_changes": lambda state: _mentioned(state, "aggregation_method") or (
        _value(state, "output_granularity") is not None
        and _value(state, "frequency") is not None
        and str(_value(state, "output_granularity")).lower() != str(_value(state, "frequency")).lower()
    ),
    "sub_daily_or_multi_timezone": lambda state: _duration_unit(state, "frequency")
    in {"second", "minute", "hour"}
    or len(_value(state, "geography") or []) > 1,
    "non_calendar_schedule": lambda state: _value(state, "calendar_type")
    in {"business_day", "trading", "academic", "custom"},
    "explicit_or_delayed_start": lambda state: _mentioned(state, "data_cutoff")
    or _mentioned(state, "lead_time"),
    "historical_cutoff_required": lambda state: _mentioned(state, "forecast_start"),
    "panel_or_hierarchical": lambda state: _value(state, "dataset_type") in {"panel", "hierarchical"},
    "hierarchical": lambda state: _value(state, "dataset_type") == "hierarchical",
    "granularity_changes_or_hierarchy": lambda state: _value(state, "dataset_type") == "hierarchical"
    or _mentioned(state, "aggregation_method"),
    "external_provider": lambda state: _value(state, "source_mode") in {"api", "catalog"},
    "probabilistic_output": lambda state: _value(state, "forecast_type") in {"probabilistic", "both"},
    "quantile_output_required": lambda state: _mentioned(state, "quantiles"),
    "source_is_upload": lambda state: _value(state, "source_mode") == "upload",
    "container_has_multiple_resources": lambda state: _value(state, "source_mode") == "database"
    or _value(state, "file_format") == "xlsx",
    "protected_source": lambda state: _source_reference(state).startswith(("private://", "database://"))
    or _mentioned(state, "authentication_reference"),
    "missing_timestamps_known": lambda state: _mentioned(state, "missing_timestamp_policy"),
    "missing_targets_known": lambda state: _mentioned(state, "missing_target_policy"),
    "duplicates_known": lambda state: _mentioned(state, "duplicate_policy"),
    "known_seasonality_true": lambda state: _value(state, "known_seasonality") is True,
    "business_or_trading_calendar": lambda state: _value(state, "calendar_type") in {"business_day", "trading"},
    "known_future_covariates_selected": lambda state: bool(_value(state, "known_future_covariates")),
    "external_covariates_selected": lambda state: any(
        item.lower().startswith("external:") for item in _selected_covariates(state)
    ),
    "sensitive_data_true": lambda state: _value(state, "contains_sensitive_data") is True,
    "source_selected": lambda state: _value(state, "source_mode") is not None,
}


def is_slot_active(definition: SlotDefinition, state: DialogueState) -> bool:
    if definition.activation_rule is None:
        return True
    try:
        predicate = RULES[definition.activation_rule]
    except KeyError as error:
        raise KeyError(f"Unknown activation rule: {definition.activation_rule}") from error
    return predicate(state)
