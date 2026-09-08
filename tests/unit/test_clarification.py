from copy import deepcopy

from forecasting_assistant.application.clarification import (
    evaluate_readiness,
    intermediate_core_slot_ids,
    rank_priority_slots,
    select_next_slot,
)
from forecasting_assistant.domain.models import (
    Intent,
    Requiredness,
    SlotState,
    SlotStatus,
)
from forecasting_assistant.domain.schema import (
    ForecastingSchema,
    SlotDefinition,
    create_initial_state,
    load_schema,
)


def _resolved_state():
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    values = {
        "intent": "create_forecast",
        "frequency": {"periods": 1, "unit": "day"},
        "forecast_horizon": {"periods": 12, "unit": "month"},
        "dataset_type": "single_series",
        "source_mode": "upload",
        "source_reference": "sales.csv",
        "forecast_type": "point",
        "output_granularity": "daily",
        "primary_metric": "mae",
        "file_format": "csv",
        "contains_sensitive_data": False,
    }
    for definition in schema.slots:
        if definition.requiredness == Requiredness.REQUIRED:
            state.slots[definition.slot_id] = SlotState(
                slot_id=definition.slot_id,
                value=values.get(definition.slot_id, "resolved"),
                status=SlotStatus.PROVIDED,
                evidence_text="resolved",
            )
    for slot_id in ("file_format", "contains_sensitive_data", "source_reference"):
        state.slots[slot_id] = SlotState(
            slot_id=slot_id,
            value=values[slot_id],
            status=SlotStatus.PROVIDED,
            evidence_text="resolved",
        )
    return schema, state


def test_readiness_requires_active_required_and_conditional_slots() -> None:
    schema, state = _resolved_state()
    state.slots["dataset_type"] = SlotState(
        slot_id="dataset_type", value="panel", status=SlotStatus.PROVIDED, evidence_text="panel"
    )

    report = evaluate_readiness(schema, state)

    assert not report.ready
    assert "series_id_columns" in report.active_required_slots
    assert "series_id_columns" in report.unresolved_slots


def test_inferred_required_value_blocks_until_user_confirmed() -> None:
    schema, state = _resolved_state()
    state.slots["frequency"] = SlotState(
        slot_id="frequency",
        value={"periods": 1, "unit": "day"},
        status=SlotStatus.INFERRED,
        evidence_text="daily",
    )

    assert not evaluate_readiness(schema, state).ready

    state.slots["frequency"].confirmed_by_user = True
    assert evaluate_readiness(schema, state).ready


def test_inactive_conditionals_and_optional_slots_do_not_block() -> None:
    schema, state = _resolved_state()
    before = deepcopy(state)

    report = evaluate_readiness(schema, state)

    assert report.ready
    assert "hierarchy_columns" not in report.unresolved_slots
    assert "stakeholder_role" not in report.unresolved_slots
    assert state == before


def test_catalog_defers_dataset_details_until_a_dataset_is_selected() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    state.slots["source_mode"] = SlotState(
        slot_id="source_mode",
        value="catalog",
        status=SlotStatus.PROVIDED,
        evidence_text="catalog",
    )

    core_slots = intermediate_core_slot_ids(schema, state)
    report = evaluate_readiness(schema, state)

    assert "frequency" not in core_slots
    assert "dataset_type" not in core_slots
    assert "source_provider" not in report.active_required_slots
    assert "contains_sensitive_data" not in report.active_required_slots
    assert "frequency" not in report.unresolved_slots
    assert "dataset_type" not in report.unresolved_slots


def test_select_next_slot_uses_required_status_priority() -> None:
    schema, state = _resolved_state()
    cases = [
        (SlotStatus.CONFLICTING, "conflicting"),
        (SlotStatus.INVALID, "invalid"),
        (SlotStatus.UNMENTIONED, "missing"),
        (SlotStatus.AMBIGUOUS, "ambiguous"),
        (SlotStatus.INFERRED, "inferred"),
    ]

    for status, reason in cases:
        state.slots["target_column"] = SlotState(
            slot_id="target_column",
            value=None if status == SlotStatus.UNMENTIONED else "candidate",
            status=status,
            evidence_text="candidate" if status == SlotStatus.INFERRED else None,
        )
        candidate = select_next_slot(schema, state)
        assert candidate is not None
        assert candidate.slot_id == "target_column"
        assert reason in candidate.reason
        state.slots["target_column"] = SlotState(
            slot_id="target_column",
            value="resolved",
            status=SlotStatus.PROVIDED,
            evidence_text="resolved",
        )


def test_active_conditional_precedes_high_impact_optional() -> None:
    conditional = SlotDefinition(
        slot_id="conditional",
        area="test",
        description="Conditional slot.",
        value_type="string",
        requiredness=Requiredness.CONDITIONAL,
        activation_rule=None,
        static_question="Conditional?",
    )
    optional = SlotDefinition(
        slot_id="optional",
        area="test",
        description="Optional slot.",
        value_type="string",
        requiredness=Requiredness.OPTIONAL,
        static_question="Optional?",
        priority_weight=100,
    )
    schema = ForecastingSchema(slots=(conditional, optional))
    state = create_initial_state(schema)

    candidate = select_next_slot(schema, state)

    assert candidate is not None
    assert candidate.slot_id == "conditional"


def test_high_impact_optional_can_block_and_be_selected() -> None:
    optional = SlotDefinition(
        slot_id="optional",
        area="test",
        description="Optional slot.",
        value_type="string",
        requiredness=Requiredness.OPTIONAL,
        static_question="Optional?",
        priority_weight=80,
    )
    schema = ForecastingSchema(slots=(optional,))
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST

    assert not evaluate_readiness(schema, state).ready
    assert select_next_slot(schema, state).slot_id == "optional"


def test_data_source_is_asked_before_dataset_column_questions() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    state.slots["intent"] = SlotState(
        slot_id="intent",
        value=Intent.CREATE_FORECAST.value,
        status=SlotStatus.PROVIDED,
        evidence_text="forecast",
    )

    candidate = select_next_slot(schema, state)

    assert candidate is not None
    assert candidate.slot_id == "source_mode"


def test_source_reference_is_asked_before_target_column_after_source_mode() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    state.slots["intent"] = SlotState(
        slot_id="intent",
        value=Intent.CREATE_FORECAST.value,
        status=SlotStatus.PROVIDED,
        evidence_text="forecast",
    )
    state.slots["source_mode"] = SlotState(
        slot_id="source_mode",
        value="upload",
        status=SlotStatus.PROVIDED,
        evidence_text="upload",
    )

    candidate = select_next_slot(schema, state)

    assert candidate is not None
    assert candidate.slot_id == "source_reference"


def test_catalog_mode_does_not_ask_novice_for_internal_source_identifier() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    state.slots["intent"] = SlotState(
        slot_id="intent",
        value=Intent.CREATE_FORECAST.value,
        status=SlotStatus.PROVIDED,
        evidence_text="forecast",
    )
    state.slots["source_mode"] = SlotState(
        slot_id="source_mode",
        value="catalog",
        status=SlotStatus.PROVIDED,
        evidence_text="catalog",
    )

    candidate = select_next_slot(schema, state)

    assert candidate is not None
    assert candidate.slot_id != "source_reference"


def test_catalog_mode_defers_dataset_questions_until_schema_is_available() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    state.slots["intent"] = SlotState(
        slot_id="intent",
        value=Intent.CREATE_FORECAST.value,
        status=SlotStatus.PROVIDED,
        evidence_text="forecast",
    )
    state.slots["source_mode"] = SlotState(
        slot_id="source_mode",
        value="catalog",
        status=SlotStatus.PROVIDED,
        evidence_text="catalog",
    )

    core_ids = set(intermediate_core_slot_ids(schema, state))
    ranked_ids = {item["slot_id"] for item in rank_priority_slots(schema, state)}

    assert not core_ids.intersection(
        {"target_column", "time_column", "dataset_type", "series_id_columns", "hierarchy_columns"}
    )
    assert not ranked_ids.intersection(
        {"target_column", "time_column", "dataset_type", "series_id_columns", "hierarchy_columns"}
    )


def test_catalog_mode_reactivates_dataset_questions_after_schema_is_available() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST
    state.slots["intent"] = SlotState(
        slot_id="intent",
        value=Intent.CREATE_FORECAST.value,
        status=SlotStatus.PROVIDED,
        evidence_text="forecast",
    )
    state.slots["source_mode"] = SlotState(
        slot_id="source_mode",
        value="catalog",
        status=SlotStatus.PROVIDED,
        evidence_text="catalog",
    )
    state.dataset_columns = ["date", "country", "inflation"]

    core_ids = set(intermediate_core_slot_ids(schema, state))

    assert {"target_column", "time_column", "dataset_type"} <= core_ids


def test_priority_slots_are_numbered_for_the_intermediate_interview() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST

    ranked = rank_priority_slots(schema, state)

    assert ranked
    assert len(ranked) <= 12
    assert [item["rank"] for item in ranked] == list(range(1, len(ranked) + 1))
    assert all(
        {"rank", "slot_id", "question", "priority", "status", "aspect", "dimension", "gate_status"}
        <= set(item)
        for item in ranked
    )
    assert ranked[0]["priority"] >= ranked[-1]["priority"]


def test_forecast_intent_is_gate_pruned_from_priority_slots() -> None:
    schema = load_schema()
    state = create_initial_state(schema)
    state.intent = Intent.CREATE_FORECAST

    ranked = rank_priority_slots(schema, state)

    assert "intent" not in {item["slot_id"] for item in ranked}


def test_intermediate_readiness_stops_before_advanced_machine_learning_details() -> None:
    schema, state = _resolved_state()
    state.slots["business_goal"] = SlotState(slot_id="business_goal")
    state.slots["success_criteria"] = SlotState(slot_id="success_criteria")
    state.slots["forecast_type"] = SlotState(slot_id="forecast_type")
    state.slots["primary_metric"] = SlotState(slot_id="primary_metric")

    report = evaluate_readiness(schema, state)

    assert report.ready
    assert {"business_goal", "success_criteria", "forecast_type", "primary_metric"} <= set(
        report.unresolved_slots
    )
