from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIVE_EVAL_USER_ID = "live-evaluation-user"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forecasting_assistant.application.clarification import select_next_slot
from forecasting_assistant.application.dataset_discovery import (
    DatasetDiscoveryService,
)
from forecasting_assistant.application.orchestrator import ElicitationEngine
from forecasting_assistant.config import get_settings
from forecasting_assistant.domain.schema import load_schema
from forecasting_assistant.infrastructure.datasets.http import SecureHttpClient
from forecasting_assistant.infrastructure.datasets.object_store import (
    ContentAddressedObjectStore,
)
from forecasting_assistant.infrastructure.datasets.registry import (
    build_default_adapters,
)
from forecasting_assistant.infrastructure.datasets.sqlite_repository import (
    SQLiteDatasetCatalogRepository,
)
from forecasting_assistant.infrastructure.llm.openai_responses import (
    PersistentOpenAIResponsesClient,
)
from forecasting_assistant.infrastructure.observability.pipeline_logger import (
    JsonlPipelineLogger,
)
from forecasting_assistant.infrastructure.persistence.sqlite_repository import (
    SQLiteDialogueRepository,
)


def _load_scenarios(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("scenario file must contain a non-empty JSON list")
    return [item for item in payload if isinstance(item, dict)]


def _write_upload(workdir: Path, scenario: dict[str, Any]) -> tuple[str, list[str]] | None:
    specification = scenario.get("uploaded_file")
    if not isinstance(specification, dict):
        return None
    filename = str(specification.get("filename", "upload.csv"))
    columns = [str(item) for item in specification.get("columns", [])]
    row_count = int(specification.get("csv_rows", 40))
    path = workdir / filename
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for index in range(row_count):
            writer.writerow(
                {
                    column: (
                        f"2024-{(index % 12) + 1:02d}-01"
                        if column == "date"
                        else (f"store-{index % 2 + 1}" if column == "store" else "product-a" if column == "product" else str(100 + index))
                    )
                    for column in columns
                }
            )
    return str(path), columns


def _answer_for_slot(scenario: dict[str, Any], slot_id: str) -> str:
    answers = scenario.get("answers", {})
    if isinstance(answers, dict) and slot_id in answers:
        return str(answers[slot_id])
    defaults = {
        "intent": "yes",
        "business_goal": "planning and monitoring",
        "success_criteria": "a useful forecast with low error",
        "target_description": "the requested target",
        "target_unit": "the target's normal unit",
        "frequency": "monthly",
        "forecast_horizon": "12 months",
        "dataset_type": "one overall series",
        "output_granularity": "one result for each time period",
        "contains_sensitive_data": "no",
        "source_mode": "the catalog",
        "source_reference": "the selected file",
        "forecast_type": "one predicted value",
        "primary_metric": "MAE",
    }
    return defaults.get(slot_id, str(scenario.get("initial_message", "the requested forecast")))


def _build_engine(workdir: Path) -> tuple[ElicitationEngine, SQLiteDialogueRepository]:
    settings = get_settings()
    schema = load_schema(settings.schema_version)
    repository = SQLiteDialogueRepository(workdir / "elicitation.db")
    repository.initialize()
    trace_sink = JsonlPipelineLogger(workdir / "pipeline.jsonl")
    provider = PersistentOpenAIResponsesClient(
        settings.openai_api_key,
        settings.openai_model,
        schema,
        trace_sink=trace_sink,
    )
    return ElicitationEngine(schema, provider, repository, trace_sink=trace_sink), repository


def _build_dataset_service(workdir: Path) -> DatasetDiscoveryService:
    settings = get_settings()
    catalog_repository = SQLiteDatasetCatalogRepository(workdir / "elicitation.db")
    catalog_repository.initialize()
    adapters = build_default_adapters(SecureHttpClient(), settings=settings)
    return DatasetDiscoveryService(
        adapters,
        catalog_repository,
        ContentAddressedObjectStore(workdir / "dataset_store"),
    )


async def _run_scenario(scenario: dict[str, Any], workdir: Path) -> dict[str, Any]:
    engine, _ = _build_engine(workdir)
    state = engine.start_dialogue()
    upload = _write_upload(workdir, scenario)
    if upload is not None:
        source_path, columns = upload
        state = engine.attach_uploaded_file(
            state.dialogue_id,
            source_reference=source_path,
            filename=Path(source_path).name,
            columns=columns,
        )

    transcript: list[dict[str, Any]] = []
    message = str(scenario["initial_message"])
    clarification_used = False
    clarification_slot: str | None = None
    started = time.perf_counter()
    specification = None
    failure: str | None = None

    for _ in range(8):
        turn_started = time.perf_counter()
        try:
            result = await engine.handle_user_message(state.dialogue_id, message)
        except Exception as error:  # noqa: BLE001 - report scenario failure without stopping the suite
            failure = f"{type(error).__name__}: {error}"
            break
        turn = {
            "user": message,
            "assistant": result.assistant_message,
            "elapsed_ms": round((time.perf_counter() - turn_started) * 1000, 2),
            "pending_slot": None,
            "ready": result.readiness.ready,
        }
        state = result.state
        if result.specification is not None:
            specification = result.specification
            transcript.append(turn)
            break

        if result.readiness.ready:
            transcript.append(turn)
            message = "yes"
            continue

        candidate = select_next_slot(load_schema(), state)
        if clarification_slot is not None:
            candidate_slot = clarification_slot
            clarification_slot = None
        else:
            candidate_slot = candidate.slot_id if candidate is not None else None
        if candidate_slot is None:
            transcript.append(turn)
            failure = "no next slot was available while the dialogue was not ready"
            break
        turn["pending_slot"] = candidate_slot
        transcript.append(turn)

        if scenario.get("clarify_after_first_question") and not clarification_used:
            clarification_used = True
            clarification_slot = candidate_slot
            message = "What do you mean by that?"
        else:
            message = _answer_for_slot(scenario, candidate_slot)

    if specification is None and failure is None:
        failure = "dialogue did not reach explicit confirmation within 8 turns"

    result: dict[str, Any] = {
        "scenario_id": scenario.get("scenario_id"),
        "title": scenario.get("title"),
        "dialogue_id": str(state.dialogue_id),
        "turn_count": len(transcript),
        "total_elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "transcript": transcript,
        "failure": failure,
    }
    if specification is None:
        return result

    service = _build_dataset_service(workdir)
    discovery_started = time.perf_counter()
    try:
        plan = service.discover_for_specification(
            specification,
            user_id=LIVE_EVAL_USER_ID,
        )
        result["discovery_elapsed_ms"] = round((time.perf_counter() - discovery_started) * 1000, 2)
        result["query"] = plan.query.model_dump(mode="json")
        result["recommendations"] = [
            {
                "candidate_id": item.candidate.candidate_id,
                "title": item.candidate.title,
                "publisher": item.candidate.publisher,
                "score": item.ranking.total,
                "eligible": item.ranking.eligible,
                "limitations": item.ranking.limitations,
                "source_url": item.candidate.source_url,
            }
            for item in plan.recommendations
        ]
        result["unavailable_count"] = len(plan.unavailable_alternatives)
        result["source_errors"] = plan.source_errors
        if plan.recommendations:
            selected = service.confirm_dataset(
                plan.plan_id,
                plan.recommendations[0].candidate.candidate_id,
                confirm=True,
                user_id=LIVE_EVAL_USER_ID,
            )
            result["selected_candidate_id"] = selected.candidate_id
            try:
                version = service.fetch_selection(selected.selection_id)
            except Exception as error:  # noqa: BLE001 - report fetch result per scenario
                result["fetch_status"] = "failed"
                result["fetch_error"] = f"{type(error).__name__}: {error}"
            else:
                result["fetch_status"] = "succeeded"
                result["dataset_version"] = {
                    "sha256": version.sha256,
                    "content_type": version.content_type,
                    "byte_size": version.byte_size,
                    "source_version": version.source_version,
                }
        else:
            result["fetch_status"] = "not_attempted_no_eligible_recommendation"
    except Exception as error:  # noqa: BLE001 - report discovery failure per scenario
        result["discovery_status"] = "failed"
        result["discovery_error"] = f"{type(error).__name__}: {error}"
    return result


async def _run_all(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        with tempfile.TemporaryDirectory(prefix="fyp-live-workflow-") as directory:
            results.append(await _run_scenario(scenario, Path(directory)))
        print(json.dumps(results[-1], ensure_ascii=False, sort_keys=True))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live persistent interview workflows sequentially.")
    parser.add_argument(
        "--scenario-file",
        type=Path,
        default=ROOT / "evaluation" / "live_workflow_scenarios.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evaluation" / "live_workflow_results.json",
    )
    args = parser.parse_args()
    scenarios = _load_scenarios(args.scenario_file)
    results = asyncio.run(_run_all(scenarios))
    args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "scenario_count": len(results)}))


if __name__ == "__main__":
    main()
