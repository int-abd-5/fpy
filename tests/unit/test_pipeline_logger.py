import json

from forecasting_assistant.infrastructure.observability.pipeline_logger import (
    JsonlPipelineLogger,
)


def test_pipeline_logger_writes_timestamped_redacted_jsonl(tmp_path) -> None:
    path = tmp_path / "logs" / "elicitation_pipeline.jsonl"
    logger = JsonlPipelineLogger(path)

    logger(
        "api.extract.request",
        {
            "model": "test-model",
            "api_key": "super-secret",
            "input": "token=also-secret",
        },
    )

    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["stage"] == "api.extract.request"
    assert records[0]["timestamp"]
    assert records[0]["payload"]["api_key"] == "[REDACTED]"
    assert "super-secret" not in path.read_text(encoding="utf-8")
    assert "also-secret" not in path.read_text(encoding="utf-8")
