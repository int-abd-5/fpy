from forecasting_assistant.domain.conditions import is_slot_active
from forecasting_assistant.domain.models import SlotStatus
from forecasting_assistant.domain.schema import create_initial_state, load_schema


def _state(**values):
    schema = load_schema()
    state = create_initial_state(schema)
    for slot_id, value in values.items():
        state.slots[slot_id].value = value
        state.slots[slot_id].status = SlotStatus.PROVIDED
    return schema, state


def test_panel_dataset_activates_series_identifiers() -> None:
    schema, state = _state(dataset_type="panel")

    assert is_slot_active(schema.get("series_id_columns"), state)
    assert not is_slot_active(schema.get("hierarchy_columns"), state)


def test_probabilistic_output_activates_intervals() -> None:
    schema, state = _state(forecast_type="probabilistic")

    assert is_slot_active(schema.get("prediction_interval_levels"), state)


def test_every_schema_activation_rule_has_expected_positive_case() -> None:
    cases = {
        "allow_negative_values": {"target_bounds": {"minimum": -1}},
        "aggregation_method": {"aggregation_method": "sum"},
        "timezone": {"frequency": {"periods": 1, "unit": "hour"}},
        "calendar_type": {"calendar_type": "business_day"},
        "forecast_start": {"data_cutoff": "2026-01-01T00:00:00Z"},
        "data_cutoff": {"forecast_start": "2026-01-01T00:00:00Z"},
        "series_id_columns": {"dataset_type": "panel"},
        "hierarchy_columns": {"dataset_type": "hierarchical"},
        "aggregation_level": {"dataset_type": "hierarchical"},
        "source_provider": {"source_mode": "api"},
        "prediction_interval_levels": {"forecast_type": "both"},
        "quantiles": {"quantiles": [0.5]},
        "file_format": {"source_mode": "upload"},
        "sheet_or_table": {"source_mode": "database"},
        "authentication_reference": {"source_reference": "private://warehouse"},
        "missing_timestamp_policy": {"missing_timestamp_policy": "reject"},
        "missing_target_policy": {"missing_target_policy": "reject"},
        "duplicate_policy": {"duplicate_policy": "reject"},
        "seasonal_periods": {"known_seasonality": True},
        "business_days_only": {"calendar_type": "trading"},
        "covariate_availability": {"known_future_covariates": ["price"]},
        "external_covariate_sources": {"past_covariates": ["external:weather"]},
        "privacy_constraints": {"contains_sensitive_data": True},
        "contains_sensitive_data": {"source_mode": "upload"},
    }
    schema = load_schema()
    for slot_id, values in cases.items():
        _, state = _state(**values)
        assert is_slot_active(schema.get(slot_id), state), slot_id


def test_unknown_activation_rule_is_rejected() -> None:
    schema, state = _state()
    definition = schema.get("timezone").model_copy(update={"activation_rule": "bogus"})

    try:
        is_slot_active(definition, state)
    except KeyError as error:
        assert "bogus" in str(error)
    else:
        raise AssertionError("unknown activation rule should fail closed")


def test_activation_normalizes_case_sensitive_enum_values() -> None:
    schema, state = _state(dataset_type="Panel", forecast_type="Probabilistic")

    assert is_slot_active(schema.get("series_id_columns"), state)
    assert is_slot_active(schema.get("prediction_interval_levels"), state)


def test_granularity_difference_activates_aggregation_level_without_aggregation_method() -> None:
    schema, state = _state(
        frequency={"periods": 1, "unit": "DAY"},
        output_granularity="WEEK",
    )

    assert is_slot_active(schema.get("aggregation_level"), state)


def test_granularity_rules_deactivate_when_frequency_and_output_match() -> None:
    schema, state = _state(
        frequency={"periods": 1, "unit": "DAY"},
        output_granularity="day",
    )

    assert not is_slot_active(schema.get("aggregation_level"), state)


def test_malformed_geography_does_not_activate_multi_timezone_rule() -> None:
    schema, state = _state(frequency={"periods": 1, "unit": "day"}, geography="PK,US")

    assert not is_slot_active(schema.get("timezone"), state)


def test_missing_condition_slots_are_inactive_instead_of_crashing() -> None:
    schema, state = _state()
    del state.slots["dataset_type"]

    assert not is_slot_active(schema.get("series_id_columns"), state)


def test_boolean_like_values_activate_and_deactivate_dependents() -> None:
    schema, state = _state(known_seasonality="YES", contains_sensitive_data="1")
    assert is_slot_active(schema.get("seasonal_periods"), state)
    assert is_slot_active(schema.get("privacy_constraints"), state)

    _, state = _state(known_seasonality="false", contains_sensitive_data="0")
    assert not is_slot_active(schema.get("seasonal_periods"), state)
    assert not is_slot_active(schema.get("privacy_constraints"), state)


def test_granularity_compares_periods_and_common_aliases() -> None:
    schema, state = _state(frequency={"periods": 2, "unit": "DAY"}, output_granularity="2 days")
    assert not is_slot_active(schema.get("aggregation_level"), state)

    state.slots["output_granularity"].value = "daily"
    assert is_slot_active(schema.get("aggregation_level"), state)


def test_all_sub_daily_aliases_activate_timezone() -> None:
    schema = load_schema()
    for unit in ("second", "seconds", "secondly", "minute", "minutes", "minutely", "hour", "hours", "hourly"):
        _, state = _state(frequency={"periods": 1, "unit": unit})
        assert is_slot_active(schema.get("timezone"), state), unit


def test_fixed_duration_magnitude_equivalence_does_not_activate_aggregation() -> None:
    schema, state = _state(frequency={"periods": 60, "unit": "minutes"}, output_granularity="hourly")

    assert not is_slot_active(schema.get("aggregation_level"), state)


def test_calendar_duration_aliases_compare_by_period_and_canonical_unit() -> None:
    schema, state = _state(frequency={"periods": 2, "unit": "quarters"}, output_granularity="2 quarterly")

    assert not is_slot_active(schema.get("aggregation_level"), state)
