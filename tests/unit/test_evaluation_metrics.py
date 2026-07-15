from scripts.evaluate_elicitation import METRIC_KEYS, compute_metrics


def test_perfect_results_produce_expected_metrics() -> None:
    records = [
        {
            "gold_intent": "create_forecast",
            "predicted_intent": "create_forecast",
            "gold_slots": {"target_column": "revenue"},
            "predicted_slots": {"target_column": "revenue"},
            "expected_questions": ["target_column"],
            "asked_questions": ["What is the target column?"],
            "successful_clarifications": 1,
            "completed": True,
            "turns_to_completion": 2,
            "unsupported_values": 0,
            "confirmation_corrected": False,
        }
    ]

    metrics = compute_metrics(records)

    assert set(metrics) == METRIC_KEYS
    assert metrics["intent_accuracy"] == 1.0
    assert metrics["slot_micro_f1"] == 1.0
    assert metrics["joint_goal_accuracy"] == 1.0
    assert metrics["clarification_precision"] == 1.0
    assert metrics["clarification_success"] == 1.0
    assert metrics["completion_rate"] == 1.0
    assert metrics["average_turns_to_completion"] == 2.0
    assert metrics["unsupported_value_rate"] == 0.0
    assert metrics["confirmation_correction_rate"] == 0.0
    assert metrics["one_question_compliance"] == 1.0


def test_empty_denominators_are_safe() -> None:
    metrics = compute_metrics(
        [
            {
                "gold_intent": "create_forecast",
                "predicted_intent": "unsupported",
                "gold_slots": {},
                "predicted_slots": {},
                "expected_questions": [],
                "asked_questions": [],
                "successful_clarifications": 0,
                "completed": False,
                "turns_to_completion": None,
                "unsupported_values": 0,
                "confirmation_corrected": False,
            }
        ]
    )

    assert set(metrics) == METRIC_KEYS
    assert all(isinstance(value, float) for value in metrics.values())

