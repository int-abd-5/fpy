import pytest

from forecasting_assistant.domain.models import Requiredness, SlotStatus
from forecasting_assistant.domain.schema import create_initial_state, load_schema


EXPECTED_SLOT_IDS = {
    "intent",
    "problem_statement",
    "business_goal",
    "stakeholder_role",
    "decision_supported",
    "success_criteria",
    "target_column",
    "target_description",
    "target_unit",
    "target_bounds",
    "allow_negative_values",
    "aggregation_method",
    "time_column",
    "frequency",
    "timezone",
    "calendar_type",
    "forecast_horizon",
    "forecast_start",
    "data_cutoff",
    "lead_time",
    "dataset_type",
    "series_id_columns",
    "hierarchy_columns",
    "aggregation_level",
    "scope_filters",
    "geography",
    "source_mode",
    "source_reference",
    "source_provider",
    "file_format",
    "sheet_or_table",
    "authentication_reference",
    "refresh_frequency",
    "history_start",
    "history_end",
    "expected_history_length",
    "minimum_training_points",
    "known_regime_changes",
    "missing_timestamp_policy",
    "missing_target_policy",
    "duplicate_policy",
    "outlier_policy",
    "invalid_value_policy",
    "minimum_coverage",
    "known_seasonality",
    "seasonal_periods",
    "business_days_only",
    "holidays",
    "special_events",
    "past_covariates",
    "known_future_covariates",
    "static_features",
    "covariate_availability",
    "external_covariate_sources",
    "forecast_type",
    "prediction_interval_levels",
    "quantiles",
    "scenario_forecasts",
    "rounding_rule",
    "output_granularity",
    "primary_metric",
    "secondary_metrics",
    "validation_strategy",
    "backtest_folds",
    "test_window",
    "baseline_model",
    "acceptable_error",
    "inference_mode",
    "prediction_frequency",
    "retraining_frequency",
    "latency_requirement",
    "output_format",
    "destination",
    "contains_sensitive_data",
    "privacy_constraints",
    "license",
    "provenance_required",
    "explainability_level",
    "human_approval_required",
}


def test_schema_has_unique_ids_and_approved_version() -> None:
    schema = load_schema()
    slot_ids = [slot.slot_id for slot in schema.slots]

    assert schema.version == "1.0.0"
    assert len(slot_ids) == 79
    assert len(slot_ids) == len(set(slot_ids))
    assert set(slot_ids) == EXPECTED_SLOT_IDS


def test_schema_rejects_unsupported_version() -> None:
    with pytest.raises(ValueError, match="Unsupported schema version: unsupported"):
        load_schema("unsupported")


def test_schema_protects_representative_slot_metadata() -> None:
    schema = load_schema()

    assert schema.get("intent").requiredness == Requiredness.REQUIRED
    assert schema.get("minimum_training_points").default_value == 30
    assert schema.get("human_approval_required").default_value is True
    assert schema.get("aggregation_method").allowed_values == (
        "sum",
        "mean",
        "last",
        "min",
        "max",
        "domain_specific",
    )
    assert schema.get("aggregation_method").activation_rule == "granularity_changes"


def test_initial_state_contains_every_slot_as_unmentioned() -> None:
    schema = load_schema()
    state = create_initial_state(schema)

    assert set(state.slots) == {slot.slot_id for slot in schema.slots}
    assert all(slot.status == SlotStatus.UNMENTIONED for slot in state.slots.values())
    assert schema.get("intent").requiredness == Requiredness.REQUIRED
