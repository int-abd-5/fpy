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
