from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from forecasting_assistant.domain.models import DialogueState, Requiredness, SlotState


class SlotDefinition(BaseModel):
    slot_id: str
    area: str
    description: str
    value_type: str
    requiredness: Requiredness
    allowed_values: tuple[str, ...] = ()
    activation_rule: str | None = None
    default_value: Any = None
    static_question: str
    priority_weight: int = Field(default=0, ge=0)


class ForecastingSchema(BaseModel):
    service: str = "forecasting_assistant"
    version: str = "1.0.0"
    slots: tuple[SlotDefinition, ...]

    def get(self, slot_id: str) -> SlotDefinition:
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        raise KeyError(slot_id)


def _slot(
    slot_id: str,
    area: str,
    description: str,
    value_type: str,
    requiredness: Requiredness,
    static_question: str,
    *,
    allowed_values: tuple[str, ...] = (),
    activation_rule: str | None = None,
    default_value: Any = None,
    priority_weight: int = 0,
) -> SlotDefinition:
    return SlotDefinition(
        slot_id=slot_id,
        area=area,
        description=description,
        value_type=value_type,
        requiredness=requiredness,
        static_question=static_question,
        allowed_values=allowed_values,
        activation_rule=activation_rule,
        default_value=default_value,
        priority_weight=priority_weight,
    )


def _build_slots() -> tuple[SlotDefinition, ...]:
    R = Requiredness.REQUIRED
    C = Requiredness.CONDITIONAL
    O = Requiredness.OPTIONAL
    D = Requiredness.DEFAULTABLE

    return (
        _slot("intent", "request", "Forecasting task intent.", "enum", R, "Do you want the system to create a time-series forecast?", allowed_values=("create_forecast",), priority_weight=100),
        _slot("problem_statement", "request", "What must be predicted.", "string", R, "What exactly do you need to predict?", priority_weight=95),
        _slot("business_goal", "request", "Why the forecast is needed.", "string", R, "What business or operational goal will this forecast support?", priority_weight=80),
        _slot("stakeholder_role", "request", "User role in the forecasting process.", "string", O, "What is your role in using or producing this forecast?"),
        _slot("decision_supported", "request", "Decision informed by the forecast.", "string", O, "What decision will be made from this forecast?"),
        _slot("success_criteria", "request", "Human definition of a useful result.", "string", R, "How will you decide whether the forecast is useful?", priority_weight=45),
        _slot("target_column", "target", "Target field name or identifier.", "string", R, "Which variable or column should be forecast?", priority_weight=100),
        _slot("target_description", "target", "Domain meaning of the target.", "string", R, "What does the target variable represent?", priority_weight=90),
        _slot("target_unit", "target", "Measurement unit of the target.", "string", R, "What unit is the target measured in?", priority_weight=75),
        _slot("target_bounds", "target", "Known valid minimum and maximum.", "object", O, "Does the target have known minimum or maximum values?"),
        _slot("allow_negative_values", "target", "Whether negative values are valid.", "boolean", C, "Can valid target values be negative?", activation_rule="target_requires_sign_rule"),
        _slot("aggregation_method", "target", "How observations are aggregated.", "enum", C, "How should multiple observations in one period be aggregated?", allowed_values=("sum", "mean", "last", "min", "max", "domain_specific"), activation_rule="granularity_changes"),
        _slot("time_column", "time", "Timestamp or period field.", "string", R, "Which column contains the timestamps or periods?", priority_weight=100),
        _slot("frequency", "time", "Native observation frequency.", "duration", R, "How often is the target observed?", priority_weight=100),
        _slot("timezone", "time", "IANA timezone for timestamps.", "timezone", C, "Which timezone do the timestamps use?", activation_rule="sub_daily_or_multi_timezone"),
        _slot("calendar_type", "time", "Calendar governing valid periods.", "enum", C, "Does the series follow calendar days, business days, trading days, or a custom calendar?", allowed_values=("calendar", "business_day", "trading", "academic", "custom"), activation_rule="non_calendar_schedule"),
        _slot("forecast_horizon", "time", "Number of future periods to predict.", "duration", R, "How far into the future should the system forecast?", priority_weight=100),
        _slot("forecast_start", "time", "Explicit first forecast period.", "datetime", C, "When should the first forecasted period begin?", activation_rule="explicit_or_delayed_start"),
        _slot("data_cutoff", "time", "Latest observation allowed.", "datetime", C, "What is the latest date that may be used as input?", activation_rule="historical_cutoff_required"),
        _slot("lead_time", "time", "Delay between forecast creation and use.", "duration", O, "How much lead time is needed before the forecast is used?"),
        _slot("dataset_type", "series", "Single, panel, or hierarchical series structure.", "enum", R, "Is this one series, multiple related series, or a hierarchy?", allowed_values=("single_series", "panel", "hierarchical"), priority_weight=85),
        _slot("series_id_columns", "series", "Entity keys for multiple series.", "string_list", C, "Which columns identify each individual series?", activation_rule="panel_or_hierarchical"),
        _slot("hierarchy_columns", "series", "Ordered hierarchy levels.", "string_list", C, "Which columns define the forecasting hierarchy from highest to lowest level?", activation_rule="hierarchical"),
        _slot("aggregation_level", "series", "Level at which forecasts are required.", "string", C, "At which level should forecasts be returned?", activation_rule="granularity_changes_or_hierarchy"),
        _slot("scope_filters", "series", "Filters limiting the forecasting scope.", "object_list", O, "Should the forecast include only particular products, locations, customers, or other subsets?"),
        _slot("geography", "series", "Geographic scope.", "string_list", O, "Which geographic areas should be included?"),
        _slot("source_mode", "source", "Data access mode.", "enum", R, "Will the data be uploaded, read from an API, read from a database, or selected from a catalog?", allowed_values=("upload", "api", "database", "catalog"), priority_weight=95),
        _slot("source_reference", "source", "Non-secret source identifier.", "string", R, "What file, endpoint, connection, or catalog entry contains the data?", priority_weight=80),
        _slot("source_provider", "source", "Source owner or provider.", "string", C, "Who provides this data source?", activation_rule="external_provider"),
        _slot("file_format", "source", "Uploaded file format.", "enum", C, "What format is the uploaded file?", allowed_values=("csv", "xlsx", "parquet", "json"), activation_rule="source_is_upload"),
        _slot("sheet_or_table", "source", "Worksheet, table, or API resource.", "string", C, "Which worksheet, table, or API resource contains the series?", activation_rule="container_has_multiple_resources"),
        _slot("authentication_reference", "source", "Reference to externally managed credentials.", "secret_reference", C, "Which stored credential reference should be used for this protected source?", activation_rule="protected_source"),
        _slot("refresh_frequency", "source", "Source update cadence.", "duration", O, "How often is the source data refreshed?"),
        _slot("history_start", "history", "Earliest available observation.", "datetime", O, "What is the earliest date in the history?"),
        _slot("history_end", "history", "Latest available observation.", "datetime", O, "What is the latest date in the history?"),
        _slot("expected_history_length", "history", "Estimated historical coverage.", "duration", O, "Approximately how much historical data is available?"),
        _slot("minimum_training_points", "history", "Minimum observations before modeling.", "integer", D, "What minimum number of observations should be required?", default_value=30),
        _slot("known_regime_changes", "history", "Known structural breaks.", "object_list", O, "Were there launches, policy changes, disruptions, or other structural breaks?"),
        _slot("missing_timestamp_policy", "quality", "Handling of missing periods.", "enum", C, "How should missing time periods be handled?", allowed_values=("reject", "insert", "resample", "review"), activation_rule="missing_timestamps_known"),
        _slot("missing_target_policy", "quality", "Handling of missing target values.", "enum", C, "How should missing target values be handled?", allowed_values=("reject", "impute", "interpolate", "retain"), activation_rule="missing_targets_known"),
        _slot("duplicate_policy", "quality", "Handling of duplicate timestamp/entity rows.", "enum", C, "How should duplicate observations be handled?", allowed_values=("reject", "aggregate", "latest", "review"), activation_rule="duplicates_known"),
        _slot("outlier_policy", "quality", "Handling of outliers.", "enum", O, "Should unusual values be kept, capped, transformed, removed, or flagged?", allowed_values=("keep", "cap", "transform", "remove", "flag")),
        _slot("invalid_value_policy", "quality", "Handling of domain-invalid values.", "enum", O, "Should invalid values be rejected, coerced, or flagged?", allowed_values=("reject", "coerce", "flag")),
        _slot("minimum_coverage", "quality", "Minimum non-missing coverage.", "percentage", O, "What minimum percentage of non-missing data is acceptable?"),
        _slot("known_seasonality", "seasonality", "Whether seasonality is expected.", "boolean", O, "Do you expect a repeating seasonal pattern?"),
        _slot("seasonal_periods", "seasonality", "Known cycles in observation periods.", "integer_list", C, "What seasonal cycles are known for this series?", activation_rule="known_seasonality_true"),
        _slot("business_days_only", "seasonality", "Whether non-business days are excluded.", "boolean", C, "Should weekends or non-business days be excluded?", activation_rule="business_or_trading_calendar"),
        _slot("holidays", "seasonality", "Relevant holiday calendars.", "string_list", O, "Which holiday calendars may affect the series?"),
        _slot("special_events", "seasonality", "Known events affecting demand.", "object_list", O, "Which promotions, campaigns, weather events, or other special events matter?"),
        _slot("past_covariates", "covariates", "Regressors observed through cutoff only.", "string_list", O, "Which additional variables are known only up to the forecast date?"),
        _slot("known_future_covariates", "covariates", "Regressors available for future periods.", "string_list", O, "Which variables will have known future values when predictions are made?"),
        _slot("static_features", "covariates", "Time-invariant entity attributes.", "string_list", O, "Which fixed attributes describe each series?"),
        _slot("covariate_availability", "covariates", "Availability timing for selected covariates.", "object_list", C, "When will each selected future covariate be available?", activation_rule="known_future_covariates_selected"),
        _slot("external_covariate_sources", "covariates", "Source mapping for external regressors.", "object_list", C, "Where will the external covariates come from?", activation_rule="external_covariates_selected"),
        _slot("forecast_type", "output", "Point or probabilistic output.", "enum", R, "Do you need point forecasts, probabilistic forecasts, or both?", allowed_values=("point", "probabilistic", "both"), priority_weight=70),
        _slot("prediction_interval_levels", "output", "Requested interval coverage levels.", "percentage_list", C, "Which prediction interval levels are required?", activation_rule="probabilistic_output"),
        _slot("quantiles", "output", "Requested forecast quantiles.", "probability_list", C, "Which forecast quantiles are required?", activation_rule="quantile_output_required"),
        _slot("scenario_forecasts", "output", "Named future scenarios.", "object_list", O, "Do you need forecasts for alternative scenarios?"),
        _slot("rounding_rule", "output", "Output rounding and precision.", "object", O, "How should forecast values be rounded?"),
        _slot("output_granularity", "output", "Temporal and entity level of output.", "string", R, "At what temporal and entity level should forecasts be returned?", priority_weight=60),
        _slot("primary_metric", "evaluation", "Primary model-comparison metric.", "enum", R, "Which metric should determine the best forecast?", allowed_values=("mae", "rmse", "mase", "smape"), priority_weight=55),
        _slot("secondary_metrics", "evaluation", "Additional report metrics.", "enum_list", O, "Which additional accuracy metrics should be reported?"),
        _slot("validation_strategy", "evaluation", "Time-series validation method.", "enum", D, "Should validation use rolling-origin or expanding windows?", allowed_values=("rolling_origin", "expanding_window"), default_value="expanding_window"),
        _slot("backtest_folds", "evaluation", "Number of historical test windows.", "integer", D, "How many backtest windows should be used?", default_value=3),
        _slot("test_window", "evaluation", "Size of each holdout window.", "duration", D, "How large should each holdout window be?", default_value={"periods": 1, "unit": "forecast_horizon"}),
        _slot("baseline_model", "evaluation", "Required baseline comparison.", "enum", D, "Which baseline model should be included?", allowed_values=("naive", "seasonal_naive"), default_value="seasonal_naive"),
        _slot("acceptable_error", "evaluation", "Domain performance threshold.", "object", O, "Is there an acceptable error threshold for deployment?"),
        _slot("inference_mode", "operations", "Batch, scheduled, or online predictions.", "enum", O, "Will forecasts be generated in batch, on a schedule, or on demand?", allowed_values=("batch", "scheduled", "online")),
        _slot("prediction_frequency", "operations", "How often forecasts are requested.", "duration", O, "How often should new forecasts be generated?"),
        _slot("retraining_frequency", "operations", "Desired model refresh cadence.", "duration", O, "How often should the model be retrained?"),
        _slot("latency_requirement", "operations", "Maximum inference latency.", "duration", O, "What response-time limit should forecasting meet?"),
        _slot("output_format", "operations", "Delivery serialization.", "enum", O, "Should results be returned as JSON, CSV, Excel, or another supported format?", allowed_values=("json", "csv", "xlsx")),
        _slot("destination", "operations", "Destination system or interface.", "string", O, "Where should completed forecasts be delivered?"),
        _slot("contains_sensitive_data", "governance", "Presence of sensitive information.", "boolean", C, "Does the source contain personal, confidential, or regulated data?", activation_rule="source_selected"),
        _slot("privacy_constraints", "governance", "Required privacy and access controls.", "string_list", C, "Which privacy or access restrictions apply?", activation_rule="sensitive_data_true"),
        _slot("license", "governance", "Data usage license.", "string", O, "What license governs use of the source data?"),
        _slot("provenance_required", "governance", "Whether detailed lineage is required.", "boolean", D, "Should detailed data provenance be included?", default_value=True),
        _slot("explainability_level", "governance", "Required forecast explanation detail.", "enum", O, "What level of model explanation is required?", allowed_values=("none", "basic", "feature_level", "detailed")),
        _slot("human_approval_required", "governance", "Human gate before model-building handoff.", "boolean", D, "Should a person approve the specification before modeling begins?", default_value=True),
    )


def load_schema(version: str = "1.0.0") -> ForecastingSchema:
    if version != "1.0.0":
        raise ValueError(f"Unsupported schema version: {version}")
    return ForecastingSchema(slots=_build_slots())


def create_initial_state(schema: ForecastingSchema) -> DialogueState:
    return DialogueState(
        schema_version=schema.version,
        slots={slot.slot_id: SlotState(slot_id=slot.slot_id) for slot in schema.slots},
    )
