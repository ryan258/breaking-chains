"""Write inspectable model-call artifacts and metadata-only JSONL events."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "password",
        "secret",
        "token",
    }
)
_REDACTED = "[REDACTED]"


class TraceWriter:
    """Persist full sanitized call artifacts beside compact operational events."""

    def __init__(
        self,
        *,
        log_root: Path,
        output_root: Path,
        secret_values: Sequence[str] = (),
    ) -> None:
        self._log_root = log_root
        self._output_root = output_root
        self._secret_values = tuple(value for value in secret_values if value)
        self._lock = threading.Lock()

    def record_model_call(
        self,
        *,
        investigation_id: str,
        call_id: str,
        event: str,
        metadata: Mapping[str, Any],
        request: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> Path:
        """Write a sanitized full artifact, then append its metadata-only event."""

        artifact_path = (
            self._output_root / "model-calls" / investigation_id / f"{call_id}.json"
        )
        artifact = {
            "investigation_id": investigation_id,
            "call_id": call_id,
            "request": self._redact(request),
            "response": self._redact(response),
        }
        self._write_json_atomically(artifact_path, artifact)

        log_event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "investigation_id": investigation_id,
            "call_id": call_id,
            **self._redact(metadata),
            "artifact_path": str(artifact_path),
        }
        self._append_jsonl(self._log_root / "forge.jsonl", log_event)
        return artifact_path

    def _redact(self, value: Any, *, key: str | None = None) -> Any:
        if key is not None and key.casefold() in _SENSITIVE_KEYS:
            return _REDACTED
        if isinstance(value, Mapping):
            return {
                str(item_key): self._redact(item, key=str(item_key))
                for item_key, item in value.items()
            }
        if isinstance(value, list | tuple):
            return [self._redact(item) for item in value]
        if isinstance(value, str):
            redacted = value
            for secret in self._secret_values:
                redacted = redacted.replace(secret, _REDACTED)
            return redacted
        return value

    def _write_json_atomically(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with self._lock:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)

    def _append_jsonl(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
