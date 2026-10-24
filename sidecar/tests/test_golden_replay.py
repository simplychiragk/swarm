"""
Tests for Stage 9: Demo Safety and Golden Run Replay.
"""

import json
import os
import pytest
from pathlib import Path
from sidecar.permissions.redaction import redact, redact_data
from sidecar.mock_runner import mock_runner
from sidecar.broadcaster import broadcaster


@pytest.mark.asyncio
async def test_golden_run_file_exists_and_scrubbed():
    golden_path = Path("data/golden_run.json")
    assert golden_path.exists(), "data/golden_run.json must exist"

    data = json.loads(golden_path.read_text(encoding="utf-8"))
    assert "events" in data
    assert len(data["events"]) > 0

    # Ensure all events have provenance: replay
    for ev in data["events"]:
        assert ev.get("provenance") == "replay"

    # Ensure no secrets leak
    text = golden_path.read_text(encoding="utf-8")
    assert "sk-" not in text
    assert "nvapi-" not in text


@pytest.mark.asyncio
async def test_golden_run_replay_streaming(monkeypatch):
    monkeypatch.setenv("SWARM_DEMO_MODE", "golden")
    monkeypatch.setenv("SWARM_PACING", "instant")

    received = []

    async def mock_broadcast(envelope, run_id="run-default", provenance="real"):
        received.append((envelope, provenance))

    monkeypatch.setattr(broadcaster, "broadcast", mock_broadcast)

    mock_runner.stop()
    started = mock_runner.start(delay_seconds=0.0)
    assert started is True

    # Await replay task completion
    if mock_runner._task:
        await mock_runner._task

    assert len(received) > 0
    # Every broadcasted event should have provenance == "replay"
    assert all(prov == "replay" for _, prov in received)
