from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from forecasting_assistant.prompts.extractor import safe_provider_value


class JsonlPipelineLogger:
    """Append one redacted, machine-readable record for every pipeline trace event."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = Lock()

    def __call__(self, stage: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "stage": stage,
            "payload": safe_provider_value(payload),
        }
        try:
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as stream:
                    json.dump(record, stream, ensure_ascii=False, sort_keys=True, default=str)
                    stream.write("\n")
        except OSError:
            # Observability must not interrupt an interview when a log path is unavailable.
            return
