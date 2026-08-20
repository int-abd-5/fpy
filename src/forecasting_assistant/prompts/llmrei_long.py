from __future__ import annotations

import json
import re

from forecasting_assistant.domain.models import QuestionOutput, QuestionRequest
from forecasting_assistant.prompts.extractor import safe_provider_value


_ANSWER_EXAMPLES = {
    "intent": "yes",
    "problem_statement": "forecast Bitcoin daily closing price",
    "business_goal": "monitor investment risk",
    "stakeholder_role": "portfolio analyst",
    "decision_supported": "decide whether to rebalance a portfolio",
    "success_criteria": "MAE below 500 USD",
    "target_column": "btc_usd_close",
    "target_description": "Bitcoin daily closing price",
    "target_unit": "USD per Bitcoin",
    "target_bounds": "minimum 0, maximum 100000",
    "allow_negative_values": "no",
    "aggregation_method": "last",
    "time_column": "date",
    "frequency": "1 day",
    "timezone": "UTC",
    "calendar_type": "calendar",
    "forecast_horizon": "7 days",
    "forecast_start": "2026-08-12T00:00:00",
    "data_cutoff": "2026-08-11T00:00:00",
    "lead_time": "1 hour",
    "dataset_type": "single_series",
    "series_id_columns": "asset_id",
    "hierarchy_columns": "country, product",
    "aggregation_level": "asset",
    "scope_filters": "asset = BTC-USD",
    "geography": "Pakistan",
    "source_mode": "upload",
    "source_reference": "bitcoin_prices.csv",
    "source_provider": "World Bank",
    "file_format": "csv",
    "sheet_or_table": "Sheet1",
    "authentication_reference": "secret://market-data",
    "refresh_frequency": "1 day",
    "history_start": "2020-01-01T00:00:00",
    "history_end": "2026-08-11T00:00:00",
    "expected_history_length": "6 years",
    "minimum_training_points": "30 observations",
    "known_regime_changes": "the 2022 market crash",
    "missing_timestamp_policy": "review",
    "missing_target_policy": "interpolate",
    "duplicate_policy": "latest",
    "outlier_policy": "flag",
    "invalid_value_policy": "reject",
    "minimum_coverage": "95 percent",
    "known_seasonality": "no",
    "seasonal_periods": "7",
    "business_days_only": "no",
    "holidays": "Pakistan public holidays",
    "special_events": "major market announcements",
    "past_covariates": "trading volume",
    "known_future_covariates": "none",
    "static_features": "asset class",
    "covariate_availability": "available before each forecast",
    "external_covariate_sources": "market data API",
    "forecast_type": "point",
    "prediction_interval_levels": "80 and 95 percent",
    "quantiles": "0.1, 0.5, 0.9",
    "scenario_forecasts": "base and stress",
    "rounding_rule": "round to 2 decimal places",
    "output_granularity": "daily per asset",
    "primary_metric": "MAE",
    "secondary_metrics": "RMSE and sMAPE",
    "validation_strategy": "expanding_window",
    "backtest_folds": "3",
    "test_window": "7 days",
    "baseline_model": "seasonal_naive",
    "acceptable_error": "MAE below 500 USD",
    "inference_mode": "scheduled",
    "prediction_frequency": "1 day",
    "retraining_frequency": "1 month",
    "latency_requirement": "5 seconds",
    "output_format": "JSON",
    "destination": "forecast dashboard",
    "contains_sensitive_data": "no",
    "privacy_constraints": "none",
    "license": "CC BY 4.0",
    "provenance_required": "yes",
    "explainability_level": "basic",
    "human_approval_required": "yes",
}


def example_answer(request: QuestionRequest) -> str:
    if request.example_answer:
        return request.example_answer
    contextual = _contextual_example(request)
    if contextual is not None:
        return contextual
    if request.slot_id in _ANSWER_EXAMPLES:
        return _ANSWER_EXAMPLES[request.slot_id]
    if request.allowed_values:
        return " or ".join(request.allowed_values)
    return "a specific value for this requirement"


def _context_value(request: QuestionRequest, slot_id: str) -> object:
    if slot_id in request.known_context:
        return request.known_context[slot_id]
    return request.confirmed_context.get(slot_id)


def _duration_unit(value: object) -> str | None:
    if not isinstance(value, dict) or value.get("unit") is None:
        return None
    return str(value["unit"]).strip().lower()


def _contextual_example(request: QuestionRequest) -> str | None:
    frequency_unit = _duration_unit(_context_value(request, "frequency"))
    if request.slot_id == "forecast_horizon" and frequency_unit is not None:
        return {
            "year": "3 years",
            "quarter": "4 quarters",
            "month": "12 months",
            "week": "4 weeks",
            "day": "7 days",
            "hour": "24 hours",
        }.get(frequency_unit, "3 periods")
    if request.slot_id == "output_granularity" and frequency_unit is not None:
        return {
            "year": "annual",
            "quarter": "quarterly",
            "month": "monthly",
            "week": "weekly",
            "day": "daily",
            "hour": "hourly",
        }.get(frequency_unit, f"one {frequency_unit} per period")
    if request.slot_id == "aggregation_level":
        dataset_type = _context_value(request, "dataset_type")
        if dataset_type == "single_series":
            return "overall series"
        if dataset_type == "panel":
            return "per entity"
        if dataset_type == "hierarchical":
            return "country and product levels"
    if request.slot_id in {"source_mode", "source_provider", "source_reference"}:
        value = _context_value(request, request.slot_id)
        if value is not None:
            return str(value)
    if request.slot_id == "target_column":
        reference = _context_value(request, "source_reference")
        if isinstance(reference, str) and reference.startswith("world-bank:"):
            return reference.rsplit(":", 1)[-1]
    if request.slot_id == "target_unit":
        target = str(_context_value(request, "target_column") or "")
        if target == "FP.CPI.TOTL.ZG":
            return "percent"
    return None


def build_question_instructions() -> str:
    return (
        "You are a forecasting requirements interviewer following LLMREI-long guidance.\n"
        "Your only goal is to elicit the selected slot in the forecasting schema.\n"
        "Ask exactly one concise question about that slot per turn.\n"
        "Use the user's wording and confirmed context, but never treat assistant text as user evidence.\n"
        "Use known_context to make the example consistent with the user's domain, frequency, and dataset type.\n"
        "Known context is not automatically confirmed; never silently change it.\n"
        "Probe ambiguity with one clarification question; do not assume, infer, or fill missing details.\n"
        "Do not ask about any other slot, feature, model, dataset, metric, target, horizon, or value.\n"
        "Do not propose features, models, datasets, metrics, or user values.\n"
        "After the question, append exactly one sentence beginning with 'Example answer:'.\n"
        "The example answer is illustrative guidance only, is not a default, and must not be presented as confirmed.\n"
        "Use the supplied example_answer and do not invent a more specific example.\n"
        "Use yes or no examples for boolean slots and the intent question.\n"
        "Return no headings, lists, summaries, analysis, or extra questions.\n"
        "Keep the complete response under 300 characters, use exactly one question mark, and do not put a question mark in the example."
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized = phrase.replace("_", " ").strip().lower()
    if not normalized:
        return False
    return re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", text.lower()) is not None


def validate_question(output: QuestionOutput, request: QuestionRequest) -> bool:
    question = output.question.strip()
    marker_match = re.search(r"\bexample answer:\s*", question, flags=re.IGNORECASE)
    if marker_match is None:
        return False
    question_part = question[: marker_match.start()].strip()
    example_part = question[marker_match.end() :].strip()
    if (
        len(question) > 300
        or question_part.count("?") != 1
        or not question_part.endswith("?")
        or not example_part
        or "?" in example_part
    ):
        return False

    for slot_id in request.other_active_slot_ids:
        if slot_id != request.slot_id and _contains_phrase(question_part, slot_id):
            return False

    confirmed_text = json.dumps(
        request.confirmed_context, ensure_ascii=False, sort_keys=True, default=str
    ).lower()
    for candidate in request.allowed_values:
        if _contains_phrase(question_part, candidate) and candidate.lower() not in confirmed_text:
            return False
    return True


def build_question_input(request: QuestionRequest) -> str:
    payload = safe_provider_value(request.model_dump(mode="python"))
    payload["example_answer"] = example_answer(request)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def static_fallback_question(request: QuestionRequest) -> QuestionOutput:
    return QuestionOutput(
        question=f"{request.static_question} Example answer: {example_answer(request)}."
    )
