from uuid import uuid4

from forecasting_assistant.application.dataset_query import query_from_specification
from forecasting_assistant.domain.models import ForecastingSpecification


def test_query_from_specification_preserves_prompt_separately_from_registry_target() -> None:
    specification = ForecastingSpecification(
        dialogue_id=uuid4(),
        schema_version="1.0.0",
        values={
            "problem_statement": "Predict Pakistan's inflation rate",
            "target_description": "percentage increase of inflation from the last year",
            "geography": ["Pakistan"],
            "frequency": {"periods": 1, "unit": "year"},
            "source_mode": "catalog",
        },
        user_provided_slots=[],
        confirmed_inferred_slots=[],
        documented_defaults={},
        unresolved_optional_slots=[],
    )

    query = query_from_specification(specification)

    assert query.prompt == (
        "Predict Pakistan's inflation rate percentage increase of inflation from the last year"
    )
    assert query.frequency == "annual"
    assert query.geography == ["Pakistan"]


def test_query_unwraps_text_wrappers_and_duration_unit_aliases() -> None:
    specification = ForecastingSpecification(
        dialogue_id=uuid4(),
        schema_version="1.0.0",
        values={
            "problem_statement": {"text": "Forecast Pakistan's GDP growth"},
            "target_description": {"text": "GDP growth rate"},
            "geography": ["Pakistan"],
            "frequency": {"periods": 1, "units": "years"},
            "source_mode": "catalog",
        },
        user_provided_slots=[],
        confirmed_inferred_slots=[],
        documented_defaults={},
        unresolved_optional_slots=[],
    )

    query = query_from_specification(specification)

    assert query.target == "GDP growth rate Forecast Pakistan's GDP growth"
    assert query.prompt == "Forecast Pakistan's GDP growth GDP growth rate"
    assert "{'text'" not in query.target
    assert query.frequency == "annual"
    assert query.geography == ["Pakistan"]
