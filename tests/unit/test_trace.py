import json
import os
from pathlib import Path

import pytest

from forge.observability.trace import TraceWriter


def test_writes_metadata_only_log_and_sanitized_full_artifact(tmp_path: Path) -> None:
    writer = TraceWriter(
        log_root=tmp_path / "logs",
        output_root=tmp_path / "outputs",
        secret_values=("super-secret-key",),
    )

    artifact_path = writer.record_model_call(
        investigation_id="inv_test",
        call_id="call_01",
        event="model_call_succeeded",
        metadata={"role": "skeptic", "model": "vendor/free", "duration_ms": 42},
        request={
            "messages": [{"role": "user", "content": "inspect this premise"}],
            "authorization": "Bearer super-secret-key",
        },
        response={"content": "A novel connection", "api_key": "super-secret-key"},
    )

    assert artifact_path == tmp_path / "outputs/model-calls/inv_test/call_01.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["request"]["messages"][0]["content"] == "inspect this premise"
    assert artifact["response"]["content"] == "A novel connection"
    serialized_artifact = artifact_path.read_text(encoding="utf-8")
    assert "super-secret-key" not in serialized_artifact
    assert artifact["request"]["authorization"] == "[REDACTED]"
    assert artifact["response"]["api_key"] == "[REDACTED]"

    log_path = tmp_path / "logs/forge.jsonl"
    event = json.loads(log_path.read_text(encoding="utf-8"))
    assert event["event"] == "model_call_succeeded"
    assert event["investigation_id"] == "inv_test"
    assert event["call_id"] == "call_01"
    assert event["artifact_path"] == str(artifact_path)
    serialized_log = log_path.read_text(encoding="utf-8")
    assert "inspect this premise" not in serialized_log
    assert "A novel connection" not in serialized_log
    assert "super-secret-key" not in serialized_log


def test_rejects_artifact_path_escape_and_uses_private_directories(tmp_path: Path) -> None:
    writer = TraceWriter(log_root=tmp_path / "logs", output_root=tmp_path / "outputs")

    with pytest.raises(ValueError):
        writer.record_model_call(
            investigation_id="../../escape",
            call_id="call_01",
            event="model_call_failed",
            metadata={},
            request={},
            response={},
        )

    writer.record_event(
        investigation_id="inv_test",
        call_id="call_01",
        event="model_call_started",
        metadata={},
    )
    assert os.stat(tmp_path / "logs").st_mode & 0o777 == 0o700
