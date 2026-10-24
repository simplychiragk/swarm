"""
Tests for Stage 10: Swarm Steering, Queueing, Interrupts, and Plan Diffs.
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from sidecar.models.contracts import (
    UserMessage,
    CardStatus,
    Lane,
)
from sidecar.agents.bus import MessageBus
from sidecar.agents.queen import QueenAgent
from sidecar.agents.worker import WorkerAgent
from sidecar.agents.run_manager import SwarmRunManager
from sidecar.storage import get_default_db_path, Database
from sidecar.storage.service import get_storage
from sidecar.main import app


@pytest.mark.asyncio
async def test_steering_modes_queue_and_interrupt(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_LLM_MODE", "mock")
    monkeypatch.setenv("SWARM_PACING", "instant")
    db_file = tmp_path / "steer_test.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))

    bus = MessageBus(run_id="run-steer-modes")
    published_cards = []
    published_messages = []

    async def mock_card(card):
        published_cards.append(card)

    async def mock_feed(msg):
        published_messages.append(msg)

    bus.publish_card_upsert = mock_card  # type: ignore
    bus.publish_feed_message = mock_feed  # type: ignore

    queen = QueenAgent(bus)

    # 1. Test Queue Mode
    msg_queue = UserMessage(
        id="msg-q1",
        text="Add dark mode toggle in navbar",
        timestamp="2026-10-24T12:00:00Z",
        mode="queue",
    )
    diff_q = await queen.steer(msg_queue, run_id="run-steer-modes")
    assert len(queen.pending_steers) == 1
    assert queen.pending_steers[0].text == "Add dark mode toggle in navbar"
    assert "Queued" in diff_q.reason

    # 2. Test Interrupt Mode
    msg_interrupt = UserMessage(
        id="msg-int1",
        text="Halt, let's rethink the header structure",
        timestamp="2026-10-24T12:01:00Z",
        mode="interrupt",
    )
    diff_int = await queen.steer(msg_interrupt, run_id="run-steer-modes")
    assert queen.is_interrupted is True
    assert any(c.id == "card-interrupt" for c in published_cards)
    assert "paused" in diff_int.reason


@pytest.mark.asyncio
async def test_mid_run_steering_adds_phone_field(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_LLM_MODE", "mock")
    monkeypatch.setenv("SWARM_PACING", "instant")
    monkeypatch.setenv("ENABLE_TINYFISH_BEES", "false")
    run_id = "run-steer-phone-test"
    db_file = tmp_path / "steer_phone.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))

    manager = SwarmRunManager()
    manager.run_id = run_id
    manager.bus.run_id = run_id

    published_cards = []
    async def mock_card(card):
        published_cards.append(card)

    manager.bus.publish_card_upsert = mock_card  # type: ignore

    # Initial start
    init_msg = UserMessage(
        id="msg-init",
        text="Build dark modern waitlist landing page",
        timestamp="2026-10-24T12:00:00Z",
    )
    await manager.handle_user_message(init_msg)
    if manager._orchestrator_task:
        await manager._orchestrator_task

    assert manager.queen.plan_done is True

    # User steers mid-run: add phone number field
    steer_msg = UserMessage(
        id="msg-steer-phone",
        text="Wait, add a phone number field too, with country code",
        timestamp="2026-10-24T12:05:00Z",
        mode="steer",
    )
    await manager.handle_user_message(steer_msg)

    # 1. Verify workspace files updated
    workspace = Path("workspace") / run_id
    index_html = (workspace / "index.html").read_text(encoding="utf-8")
    assert 'id="phone"' in index_html
    assert 'id="country-code"' in index_html

    api_py = (workspace / "api" / "main.py").read_text(encoding="utf-8")
    assert "phone: Optional[str]" in api_py
    assert "country_code: Optional[str]" in api_py

    # 2. Verify [EDITED] Whiteboard Card emitted
    edited_cards = [c for c in published_cards if "[EDITED]" in c.title]
    assert len(edited_cards) >= 1

    # 3. Verify SQLite steer receipt recorded
    storage = get_storage()
    steers = storage.get_run_steers(run_id)
    assert len(steers) >= 1
    assert steers[0]["status"] == "applied"
    assert "phone" in steers[0]["prompt"].lower()
    assert len(steers[0]["plan_diff"]["changes"]) >= 1

    # 4. Verify REST endpoint
    client = TestClient(app)
    resp = client.get(f"/runs/{run_id}/steers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert data["steers"][0]["mode"] == "steer"

    await manager.stop()
