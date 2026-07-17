from datetime import datetime, timezone

import pytest

from forecasting_assistant.application.normalization import normalize_value
from forecasting_assistant.application.validation import validate_dialogue, validate_slot
from forecasting_assistant.domain.models import SlotState, SlotStatus
from forecasting_assistant.domain.schema import create_initial_state, load_schema


def _slot(slot_id: str, value) -> SlotState:
    return SlotState(
        slot_id=slot_id,
        value=value,
        status=SlotStatus.PROVIDED,
        evidence_text=f"value for {slot_id}",
    )


def _dialogue(**values):
    schema = load_schema()
    state = create_initial_state(schema)
    for slot_id, value in values.items():
        state.slots[slot_id] = _slot(slot_id, value)
    return schema, state


def test_percentage_rejects_values_above_one_hundred() -> None:
    definition = load_schema().get("minimum_coverage")

    assert validate_slot(definition, _slot("minimum_coverage", 120))[0].code == "percentage_range"


def test_horizon_requires_positive_periods() -> None:
    schema, state = _dialogue(forecast_horizon={"periods": 0, "unit": "month"})

    assert any(issue.code == "positive_duration" for issue in validate_dialogue(schema, state))


def test_normalization_handles_schema_value_types() -> None:
    schema = load_schema()
    assert normalize_value(schema.get("forecast_type"), " Point ") == "point"
    assert normalize_value(schema.get("known_seasonality"), "YES") is True
    assert normalize_value(schema.get("prediction_interval_levels"), [80, "95"]) == [80.0, 95.0]
    assert normalize_value(schema.get("seasonal_periods"), "7, 12") == [7, 12]
    assert normalize_value(schema.get("geography"), "PK, US") == ["PK", "US"]
    assert normalize_value(schema.get("frequency"), {"periods": "2", "unit": "HOUR"}) == {
        "periods": 2,
        "unit": "hour",
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1 week", {"periods": 1.0, "unit": "week"}),
        ("10 days", {"periods": 10.0, "unit": "day"}),
        ("the following week", {"periods": 1.0, "unit": "week"}),
        ("monthly", {"periods": 1.0, "unit": "month"}),
    ],
)
def test_normalization_converts_natural_language_durations(
    value: str, expected: dict[str, object]
) -> None:
    assert normalize_value(load_schema().get("forecast_horizon"), value) == expected


def test_normalization_converts_datetimes_and_iana_timezones() -> None:
    schema = load_schema()
    value = normalize_value(schema.get("forecast_start"), "2026-01-02T03:04:05Z")

    assert value == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert normalize_value(schema.get("timezone"), "Asia/Karachi") == "Asia/Karachi"


def test_invalid_timezone_is_a_validation_issue_not_exception() -> None:
    issue = validate_slot(load_schema().get("timezone"), _slot("timezone", "Mars/Olympus"))[0]

    assert issue.code == "iana_timezone"


def test_invalid_datetime_text_is_a_validation_issue() -> None:
    issues = validate_slot(load_schema().get("forecast_start"), _slot("forecast_start", "not-a-date"))

    assert any(issue.code == "invalid_datetime" for issue in issues)


def test_cross_field_history_dates_must_be_ordered() -> None:
    schema, state = _dialogue(history_start="2026-02-01T00:00:00Z", history_end="2026-01-01T00:00:00Z")

    assert any(issue.code == "history_order" for issue in validate_dialogue(schema, state))


def test_cross_field_forecast_start_cannot_precede_cutoff() -> None:
    schema, state = _dialogue(forecast_start="2026-01-01T00:00:00Z", data_cutoff="2026-02-01T00:00:00Z")

    assert any(issue.code == "forecast_start_after_cutoff" for issue in validate_dialogue(schema, state))


def test_panel_requires_series_identifiers() -> None:
    schema, state = _dialogue(dataset_type="panel")

    assert any(issue.code == "series_id_columns_required" for issue in validate_dialogue(schema, state))


def test_hierarchical_requires_hierarchy_columns() -> None:
    schema, state = _dialogue(dataset_type="hierarchical", series_id_columns=["store"])

    assert any(issue.code == "hierarchy_columns_required" for issue in validate_dialogue(schema, state))


def test_probabilistic_output_requires_intervals_or_quantiles() -> None:
    schema, state = _dialogue(forecast_type="probabilistic")

    assert any(issue.code == "probabilistic_output_required" for issue in validate_dialogue(schema, state))


def test_future_covariates_require_availability() -> None:
    schema, state = _dialogue(known_future_covariates=["price"])

    assert any(issue.code == "covariate_availability_required" for issue in validate_dialogue(schema, state))


def test_authentication_reference_requires_secret_scheme() -> None:
    issue = validate_slot(
        load_schema().get("authentication_reference"), _slot("authentication_reference", "api-key-value")
    )[0]

    assert issue.code == "secret_reference"


def test_raw_credentials_are_rejected() -> None:
    for value in (
        "sk-test",
        "api_key=abc",
        "api key: abc",
        "access-token = abc",
        "access token: abc",
        "password=abc",
        "passwd : abc",
        "secret: abc",
        "Bearer abc",
        "token=abc",
        "AKIAIOSFODNN7EXAMPLE",
    ):
        issues = validate_slot(load_schema().get("source_reference"), _slot("source_reference", value))
        assert any(issue.code == "raw_credential" for issue in issues), value


def test_secret_references_are_not_flagged_as_raw_credentials() -> None:
    issues = validate_slot(
        load_schema().get("authentication_reference"), _slot("authentication_reference", "secret://prod-api-key")
    )

    assert not any(issue.code == "raw_credential" for issue in issues)


def test_benign_secret_phrase_is_not_a_raw_credential() -> None:
    definition = load_schema().get("source_reference")
    for value in ("token bucket.csv", "password policy.pdf", "access token guide.pdf", "secret garden.csv"):
        issues = validate_slot(definition, _slot("source_reference", value))
        assert not any(issue.code == "raw_credential" for issue in issues), value


def test_credential_assignments_and_authorization_forms_are_rejected() -> None:
    definition = load_schema().get("source_reference")
    for value in (
        "token=abc",
        "password: abc",
        '{"access_token": "abc"}',
        "https://example.test/data?token=abc",
        "Authorization: Bearer abc",
        "AKIAIOSFODNN7EXAMPLE",
    ):
        issues = validate_slot(definition, _slot("source_reference", value))
        assert any(issue.code == "raw_credential" for issue in issues), value


def test_signature_credentials_are_rejected() -> None:
    definition = load_schema().get("source_reference")
    for value in (
        "X-Amz-Signature=abc",
        "x-amz-signature: abc",
        "signature=abc",
    ):
        issues = validate_slot(definition, _slot("source_reference", value))
        assert any(issue.code == "raw_credential" for issue in issues), value


def test_signature_filename_is_not_a_raw_credential() -> None:
    definition = load_schema().get("source_reference")

    issues = validate_slot(definition, _slot("source_reference", "signature guide.pdf"))

    assert not any(issue.code == "raw_credential" for issue in issues)


def test_mixed_naive_and_aware_history_dates_return_issue() -> None:
    schema, state = _dialogue(
        history_start="2026-01-01T00:00:00",
        history_end="2026-01-02T00:00:00Z",
    )

    issues = validate_dialogue(schema, state)

    assert any(issue.code == "datetime_timezone" for issue in issues)


def test_mixed_naive_and_aware_forecast_dates_return_issue() -> None:
    schema, state = _dialogue(
        forecast_start="2026-01-02T00:00:00",
        data_cutoff="2026-01-01T00:00:00Z",
    )

    issues = validate_dialogue(schema, state)

    assert any(issue.code == "datetime_timezone" for issue in issues)


def test_missing_slot_entries_do_not_crash_dialogue_validation() -> None:
    schema, state = _dialogue(dataset_type="Panel", forecast_type="Probabilistic")
    del state.slots["series_id_columns"]
    del state.slots["prediction_interval_levels"]

    issues = validate_dialogue(schema, state)

    assert any(issue.code == "series_id_columns_required" for issue in issues)


def test_malformed_geography_is_reported_as_a_slot_issue() -> None:
    schema, state = _dialogue(geography={"country": "PK"})

    issues = validate_dialogue(schema, state)

    assert any(issue.slot_id == "geography" and issue.code == "list_type" for issue in issues)


def test_duration_rejects_non_finite_periods() -> None:
    definition = load_schema().get("forecast_horizon")

    for periods in (float("nan"), float("inf"), float("-inf")):
        issues = validate_slot(definition, _slot("forecast_horizon", {"periods": periods, "unit": "day"}))
        assert any(issue.code == "positive_duration" for issue in issues), periods


def test_case_normalization_applies_to_cross_field_requirements() -> None:
    schema, state = _dialogue(dataset_type="Panel", forecast_type="Probabilistic")

    issues = validate_dialogue(schema, state)

    assert any(issue.code == "series_id_columns_required" for issue in issues)
    assert any(issue.code == "probabilistic_output_required" for issue in issues)


def test_probability_values_must_be_between_zero_and_one() -> None:
    definition = load_schema().get("quantiles")

    assert validate_slot(definition, _slot("quantiles", [1.2]))[0].code == "probability_range"
