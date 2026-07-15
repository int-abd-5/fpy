from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.build_scenarios import build_scenarios, validate_scenarios  # noqa: E402
from forecasting_assistant.domain.schema import load_schema  # noqa: E402


METRIC_KEYS = {
    "intent_accuracy",
    "slot_micro_precision",
    "slot_micro_recall",
    "slot_micro_f1",
    "average_goal_accuracy",
    "joint_goal_accuracy",
    "clarification_precision",
    "clarification_success",
    "completion_rate",
    "average_turns_to_completion",
    "unsupported_value_rate",
    "confirmation_correction_rate",
    "one_question_compliance",
}


def _divide(numerator: float, denominator: float, *, empty: float = 0.0) -> float:
    return empty if denominator == 0 else numerator / denominator


def compute_metrics(records: list[dict[str, Any]]) -> dict[str, float]:
    if not records:
        return {key: 0.0 for key in METRIC_KEYS}
    intent_correct = 0
    true_positive = false_positive = false_negative = 0
    goal_scores: list[float] = []
    joint_correct = 0
    asked_total = relevant_questions = expected_total = successful = 0
    completed = 0
    completed_turns: list[float] = []
    unsupported = predicted_values = corrected = 0
    compliant_questions = total_questions = 0

    for record in records:
        intent_correct += record["predicted_intent"] == record["gold_intent"]
        gold = record["gold_slots"]
        predicted = record["predicted_slots"]
        correct_keys = {key for key, value in predicted.items() if key in gold and gold[key] == value}
        true_positive += len(correct_keys)
        false_positive += len(predicted) - len(correct_keys)
        false_negative += len(gold) - len(correct_keys)
        goal_scores.append(_divide(len(correct_keys), len(gold), empty=1.0))
        joint_correct += predicted == gold

        expected = record.get("expected_questions", [])
        asked = record.get("asked_questions", [])
        expected_total += len(expected)
        asked_total += len(asked)
        for question in asked:
            normalized = question.lower()
            if any(slot_id.replace("_", " ") in normalized for slot_id in expected):
                relevant_questions += 1
            total_questions += 1
            compliant_questions += question.count("?") == 1
        successful += int(record.get("successful_clarifications", 0))

        if record.get("completed"):
            completed += 1
            turns = record.get("turns_to_completion")
            if turns is not None:
                completed_turns.append(float(turns))
        unsupported += int(record.get("unsupported_values", 0))
        predicted_values += len(predicted)
        corrected += bool(record.get("confirmation_corrected"))

    precision = _divide(true_positive, true_positive + false_positive, empty=1.0)
    recall = _divide(true_positive, true_positive + false_negative, empty=1.0)
    f1 = _divide(2 * precision * recall, precision + recall, empty=0.0)
    return {
        "intent_accuracy": _divide(intent_correct, len(records)),
        "slot_micro_precision": precision,
        "slot_micro_recall": recall,
        "slot_micro_f1": f1,
        "average_goal_accuracy": sum(goal_scores) / len(goal_scores),
        "joint_goal_accuracy": _divide(joint_correct, len(records)),
        "clarification_precision": _divide(
            relevant_questions, asked_total, empty=1.0 if expected_total == 0 else 0.0
        ),
        "clarification_success": _divide(successful, expected_total, empty=1.0),
        "completion_rate": _divide(completed, len(records)),
        "average_turns_to_completion": (
            sum(completed_turns) / len(completed_turns) if completed_turns else 0.0
        ),
        "unsupported_value_rate": _divide(unsupported, predicted_values, empty=0.0),
        "confirmation_correction_rate": _divide(corrected, len(records)),
        "one_question_compliance": _divide(
            compliant_questions, total_questions, empty=1.0
        ),
    }


def _fake_record(scenario: dict[str, Any], condition: str) -> dict[str, Any]:
    predicted = dict(scenario["gold_slots"])
    expected = list(scenario["expected_questions"])
    asked: list[str] = []
    completed = True
    unsupported = 0
    successful = 0
    if condition == "hybrid":
        asked = [f"What is the {slot_id.replace('_', ' ')}?" for slot_id in expected]
        successful = len(expected)
    elif condition == "schema_no_clarification":
        if expected and predicted:
            predicted.pop(next(iter(predicted)))
            completed = False
    elif condition == "unrestricted_llmrei_long":
        predicted["unsupported_model_choice"] = "transformer"
        unsupported = 1
        asked = [f"What is the {slot_id.replace('_', ' ')}? Any other details?" for slot_id in expected]
        successful = len(expected)
    else:
        raise ValueError(f"unsupported condition: {condition}")
    return {
        **scenario,
        "predicted_intent": scenario["gold_intent"],
        "predicted_slots": predicted,
        "asked_questions": asked,
        "successful_clarifications": successful,
        "completed": completed,
        "turns_to_completion": len(scenario["turns"]) + len(asked) if completed else None,
        "unsupported_values": unsupported,
        "confirmation_corrected": scenario["category"] == "contradictory",
    }


def evaluate(condition: str, client: str) -> dict[str, Any]:
    if client != "fake":
        raise ValueError("only the deterministic fake client is supported by this milestone")
    scenarios = build_scenarios()
    validate_scenarios(scenarios, load_schema())
    records = [_fake_record(scenario, condition) for scenario in scenarios]
    return {
        "condition": condition,
        "client": client,
        "scenario_count": len(records),
        "metrics": compute_metrics(records),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--condition",
        choices=("hybrid", "schema_no_clarification", "unrestricted_llmrei_long", "all"),
        default="all",
    )
    parser.add_argument("--client", choices=("fake",), default="fake")
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args()
    conditions = (
        ("hybrid", "schema_no_clarification", "unrestricted_llmrei_long")
        if args.condition == "all"
        else (args.condition,)
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for condition in conditions:
        result = evaluate(condition, args.client)
        path = args.output_dir / f"{condition}.json"
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
