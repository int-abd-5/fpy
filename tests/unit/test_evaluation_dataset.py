import json
from collections import Counter
from pathlib import Path

from evaluation.build_scenarios import EXPECTED_COUNTS, build_scenarios, validate_scenarios
from forecasting_assistant.domain.schema import load_schema


def test_dataset_has_exact_counts_unique_ids_and_valid_slots() -> None:
    scenarios = build_scenarios()
    validate_scenarios(scenarios, load_schema())

    assert len(scenarios) == 60
    assert Counter(item["category"] for item in scenarios) == EXPECTED_COUNTS
    assert len({item["scenario_id"] for item in scenarios}) == 60
    assert all(item["turns"] and all(turn.strip() for turn in item["turns"]) for item in scenarios)
    assert all(item["must_not_infer"] for item in scenarios)
    assert all(
        item["expected_questions"]
        for item in scenarios
        if item["category"] != "complete"
    )


def test_committed_jsonl_is_stable_and_matches_builder() -> None:
    path = Path("evaluation/scenarios.jsonl")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert rows == build_scenarios()
    assert [row["scenario_id"] for row in rows] == sorted(
        row["scenario_id"] for row in rows
    )

