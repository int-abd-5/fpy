from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from forecasting_assistant.domain.schema import ForecastingSchema, load_schema


EXPECTED_COUNTS = {
    "complete": 15,
    "missing_required": 15,
    "ambiguous": 10,
    "multi_series": 10,
    "contradictory": 5,
    "probabilistic_covariate": 5,
}

BASE_GOLD = {
    "target_description": "store sales",
    "frequency": {"periods": 1, "unit": "month"},
    "forecast_horizon": {"periods": 12, "unit": "month"},
    "source_mode": "upload",
    "file_format": "csv",
}


def _case(
    scenario_id: str,
    category: str,
    turns: list[str],
    *,
    gold_slots: dict[str, Any] | None = None,
    expected_questions: list[str] | None = None,
    must_not_infer: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "category": category,
        "turns": turns,
        "gold_intent": "create_forecast",
        "gold_slots": {**BASE_GOLD, **(gold_slots or {})},
        "expected_questions": expected_questions or [],
        "must_not_infer": must_not_infer or ["target_column", "time_column"],
    }


CASES = (
    _case("complete-001", "complete", ["Forecast monthly store sales for 12 months from sales.csv."]),
    _case("complete-002", "complete", ["Create a 12-month monthly revenue forecast from revenue.csv."]),
    _case("complete-003", "complete", ["Predict monthly demand for one year using demand.csv."]),
    _case("complete-004", "complete", ["Forecast monthly unit sales for 12 periods from units.csv."]),
    _case("complete-005", "complete", ["Produce monthly bookings forecasts for the next year from bookings.csv."]),
    _case("complete-006", "complete", ["Estimate monthly orders for 12 months using orders.csv."]),
    _case("complete-007", "complete", ["Forecast monthly collections for one year from collections.csv."]),
    _case("complete-008", "complete", ["Predict monthly website traffic for 12 months using traffic.csv."]),
    _case("complete-009", "complete", ["Create monthly call-volume forecasts for one year from calls.csv."]),
    _case("complete-010", "complete", ["Forecast monthly energy demand for 12 months from energy.csv."]),
    _case("complete-011", "complete", ["Predict monthly production output for one year using output.csv."]),
    _case("complete-012", "complete", ["Forecast monthly claims for 12 months from claims.csv."]),
    _case("complete-013", "complete", ["Estimate monthly shipments for one year using shipments.csv."]),
    _case("complete-014", "complete", ["Forecast monthly subscriptions for 12 months from subscriptions.csv."]),
    _case("complete-015", "complete", ["Predict monthly cash flow for one year using cashflow.csv."]),
    _case("missing-required-001", "missing_required", ["Forecast sales from sales.csv."], expected_questions=["frequency"]),
    _case("missing-required-002", "missing_required", ["Forecast monthly sales from sales.csv."], expected_questions=["forecast_horizon"]),
    _case("missing-required-003", "missing_required", ["Forecast monthly sales for 12 months."], expected_questions=["source_reference"]),
    _case("missing-required-004", "missing_required", ["Use sales.csv for a monthly 12-month forecast."], expected_questions=["target_description"]),
    _case("missing-required-005", "missing_required", ["Forecast monthly store sales for one year."], expected_questions=["source_mode"]),
    _case("missing-required-006", "missing_required", ["Forecast revenue monthly from revenue.csv."], expected_questions=["forecast_horizon"]),
    _case("missing-required-007", "missing_required", ["Forecast demand for 12 months from demand.csv."], expected_questions=["frequency"]),
    _case("missing-required-008", "missing_required", ["Create a monthly forecast from orders.csv."], expected_questions=["target_description"]),
    _case("missing-required-009", "missing_required", ["Predict monthly traffic for a year."], expected_questions=["source_reference"]),
    _case("missing-required-010", "missing_required", ["Use calls.csv to make a forecast."], expected_questions=["frequency"]),
    _case("missing-required-011", "missing_required", ["Forecast energy monthly from energy.csv."], expected_questions=["forecast_horizon"]),
    _case("missing-required-012", "missing_required", ["Forecast production for one year from output.csv."], expected_questions=["frequency"]),
    _case("missing-required-013", "missing_required", ["Forecast monthly claims for 12 months."], expected_questions=["source_reference"]),
    _case("missing-required-014", "missing_required", ["Forecast shipments from shipments.csv."], expected_questions=["frequency"]),
    _case("missing-required-015", "missing_required", ["Create a 12-month monthly forecast from data.csv."], expected_questions=["target_description"]),
    _case("ambiguous-001", "ambiguous", ["Forecast sales regularly for a while from sales.csv."], expected_questions=["frequency"]),
    _case("ambiguous-002", "ambiguous", ["Forecast demand monthly for the near future from demand.csv."], expected_questions=["forecast_horizon"]),
    _case("ambiguous-003", "ambiguous", ["Forecast the value column monthly for 12 months from data.csv."], expected_questions=["target_description"]),
    _case("ambiguous-004", "ambiguous", ["Use the latest spreadsheet to forecast sales monthly."], expected_questions=["source_reference"]),
    _case("ambiguous-005", "ambiguous", ["Forecast revenue for 12 periods from revenue.csv."], expected_questions=["frequency"]),
    _case("ambiguous-006", "ambiguous", ["Predict orders monthly using the orders source."], expected_questions=["source_mode"]),
    _case("ambiguous-007", "ambiguous", ["Forecast traffic monthly for 12 months from traffic.csv, maybe visits."], expected_questions=["target_description"]),
    _case("ambiguous-008", "ambiguous", ["Forecast monthly energy for a year using data."], expected_questions=["source_reference"]),
    _case("ambiguous-009", "ambiguous", ["Predict claims at the usual cadence for one year."], expected_questions=["frequency"]),
    _case("ambiguous-010", "ambiguous", ["Forecast subscriptions monthly for a useful horizon."], expected_questions=["forecast_horizon"]),
    _case("multi-series-001", "multi_series", ["Forecast monthly sales by store for 12 months from sales.csv."], gold_slots={"dataset_type": "panel", "series_id_columns": ["store_id"]}, expected_questions=["series_id_columns"]),
    _case("multi-series-002", "multi_series", ["Forecast demand by product monthly for a year."], gold_slots={"dataset_type": "panel", "series_id_columns": ["product_id"]}, expected_questions=["series_id_columns"]),
    _case("multi-series-003", "multi_series", ["Forecast store and region sales hierarchically."], gold_slots={"dataset_type": "hierarchical", "series_id_columns": ["store_id"], "hierarchy_columns": ["region", "store_id"]}, expected_questions=["hierarchy_columns"]),
    _case("multi-series-004", "multi_series", ["Predict monthly orders per customer for 12 months."], gold_slots={"dataset_type": "panel", "series_id_columns": ["customer_id"]}, expected_questions=["series_id_columns"]),
    _case("multi-series-005", "multi_series", ["Forecast SKU demand by warehouse monthly."], gold_slots={"dataset_type": "panel", "series_id_columns": ["sku", "warehouse"]}, expected_questions=["series_id_columns"]),
    _case("multi-series-006", "multi_series", ["Forecast national, region, and store sales as a hierarchy."], gold_slots={"dataset_type": "hierarchical", "series_id_columns": ["store_id"], "hierarchy_columns": ["country", "region", "store_id"]}, expected_questions=["aggregation_level"]),
    _case("multi-series-007", "multi_series", ["Predict monthly traffic per website for one year."], gold_slots={"dataset_type": "panel", "series_id_columns": ["site_id"]}, expected_questions=["series_id_columns"]),
    _case("multi-series-008", "multi_series", ["Forecast claims by branch monthly."], gold_slots={"dataset_type": "panel", "series_id_columns": ["branch_id"]}, expected_questions=["series_id_columns"]),
    _case("multi-series-009", "multi_series", ["Forecast category and SKU shipments hierarchically."], gold_slots={"dataset_type": "hierarchical", "series_id_columns": ["sku"], "hierarchy_columns": ["category", "sku"]}, expected_questions=["hierarchy_columns"]),
    _case("multi-series-010", "multi_series", ["Predict subscriptions by plan each month for a year."], gold_slots={"dataset_type": "panel", "series_id_columns": ["plan_id"]}, expected_questions=["series_id_columns"]),
    _case("contradictory-001", "contradictory", ["Forecast sales monthly.", "Actually use weekly observations."], gold_slots={"frequency": {"periods": 1, "unit": "week"}}, expected_questions=["frequency"]),
    _case("contradictory-002", "contradictory", ["Forecast revenue for 12 months.", "Change the horizon to 6 months."], gold_slots={"forecast_horizon": {"periods": 6, "unit": "month"}}, expected_questions=["forecast_horizon"]),
    _case("contradictory-003", "contradictory", ["Use sales.csv.", "No, use revised_sales.csv."], gold_slots={"source_reference": "revised_sales.csv"}, expected_questions=["source_reference"]),
    _case("contradictory-004", "contradictory", ["Forecast total sales.", "I meant net revenue."], gold_slots={"target_description": "net revenue"}, expected_questions=["target_description"]),
    _case("contradictory-005", "contradictory", ["Use point forecasts.", "Instead provide probabilistic forecasts."], gold_slots={"forecast_type": "probabilistic", "prediction_interval_levels": [80, 95]}, expected_questions=["prediction_interval_levels"]),
    _case("probabilistic-covariate-001", "probabilistic_covariate", ["Forecast monthly sales with 80 and 95 percent intervals using planned promotions."], gold_slots={"forecast_type": "probabilistic", "prediction_interval_levels": [80, 95], "known_future_covariates": ["promotion"], "covariate_availability": [{"name": "promotion", "available": "before forecast"}]}, expected_questions=["covariate_availability"]),
    _case("probabilistic-covariate-002", "probabilistic_covariate", ["Predict demand quantiles with future prices."], gold_slots={"forecast_type": "probabilistic", "quantiles": [0.1, 0.5, 0.9], "known_future_covariates": ["price"], "covariate_availability": [{"name": "price", "available": "planned"}]}, expected_questions=["quantiles"]),
    _case("probabilistic-covariate-003", "probabilistic_covariate", ["Forecast monthly energy with weather scenarios and intervals."], gold_slots={"forecast_type": "both", "prediction_interval_levels": [90], "known_future_covariates": ["weather"], "covariate_availability": [{"name": "weather", "available": "forecast"}]}, expected_questions=["covariate_availability"]),
    _case("probabilistic-covariate-004", "probabilistic_covariate", ["Provide probabilistic order forecasts using campaign plans."], gold_slots={"forecast_type": "probabilistic", "prediction_interval_levels": [95], "known_future_covariates": ["campaign"], "covariate_availability": [{"name": "campaign", "available": "scheduled"}]}, expected_questions=["prediction_interval_levels"]),
    _case("probabilistic-covariate-005", "probabilistic_covariate", ["Forecast traffic quantiles using known holiday indicators."], gold_slots={"forecast_type": "probabilistic", "quantiles": [0.25, 0.5, 0.75], "known_future_covariates": ["holiday"], "covariate_availability": [{"name": "holiday", "available": "calendar"}]}, expected_questions=["covariate_availability"]),
)


def build_scenarios() -> list[dict[str, Any]]:
    return sorted((dict(item) for item in CASES), key=lambda item: item["scenario_id"])


def validate_scenarios(
    scenarios: list[dict[str, Any]], schema: ForecastingSchema
) -> None:
    ids = [item["scenario_id"] for item in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("scenario IDs must be unique")
    counts = Counter(item["category"] for item in scenarios)
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"scenario category counts differ: {counts}")
    known_slots = {slot.slot_id for slot in schema.slots}
    for item in scenarios:
        if not item["turns"] or any(not str(turn).strip() for turn in item["turns"]):
            raise ValueError(f"scenario {item['scenario_id']} has an empty turn")
        unknown = set(item["gold_slots"]) - known_slots
        if unknown:
            raise ValueError(f"scenario {item['scenario_id']} has unknown slots: {unknown}")
        if item["category"] != "complete" and not item["expected_questions"]:
            raise ValueError(f"scenario {item['scenario_id']} needs an expected question")
        if not item["must_not_infer"]:
            raise ValueError(f"scenario {item['scenario_id']} needs must_not_infer assertions")


def main() -> None:
    scenarios = build_scenarios()
    validate_scenarios(scenarios, load_schema())
    output = Path(__file__).with_name("scenarios.jsonl")
    output.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in scenarios),
        encoding="utf-8",
    )
    print(f"wrote {len(scenarios)} scenarios to {output}")


if __name__ == "__main__":
    main()
