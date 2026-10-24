"""
Tests for Stage 11: Decision Layer Message Delivery, Jev Fallback, and Whiteboard Filtering.
"""

import os
import pytest
from fastapi.testclient import TestClient

from sidecar.models.contracts import (
    FeedMessage,
    AgentSender,
    Lane,
    MessageType,
)
from sidecar.decision import RuleBasedDecisionLayer
from sidecar.storage import get_default_db_path, Database
from sidecar.storage.service import get_storage
from sidecar.main import app


@pytest.mark.asyncio
async def test_decide_delivery_rules(monkeypatch, tmp_path):
    run_id = "run-decision-test-1"
    db_file = tmp_path / "decisions.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))

    layer = RuleBasedDecisionLayer()

    # 1. Scribe receives all messages
    msg1 = FeedMessage(
        id="msg-1",
        timestamp="2026-10-24T12:00:00Z",
        sender=AgentSender.WORKER,
        lane=Lane.BE,
        type=MessageType.CHAT,
        content="General progress update",
    )
    d1 = layer.decide_delivery(msg1, "scribe", run_id=run_id)
    assert d1["action"] == "deliver"
    assert d1["confidence"] == 1.0

    # 2. Directed message to another agent is dropped
    msg_directed = FeedMessage(
        id="msg-2",
        timestamp="2026-10-24T12:00:01Z",
        sender=AgentSender.WORKER,
        lane=Lane.BE,
        type=MessageType.CHAT,
        content="Hey QA bee, check this out",
        to="qa_bee",
    )
    d_fe = layer.decide_delivery(msg_directed, "fe_worker", run_id=run_id)
    assert d_fe["action"] == "drop"

    d_qa = layer.decide_delivery(msg_directed, "qa_bee", run_id=run_id)
    assert d_qa["action"] == "deliver"

    # 3. Pure SQL message is dropped for FE worker
    msg_sql = FeedMessage(
        id="msg-3",
        timestamp="2026-10-24T12:00:02Z",
        sender=AgentSender.WORKER,
        lane=Lane.BE,
        type=MessageType.CHAT,
        content="Running SQL migration: ALTER TABLE waitlist ADD COLUMN extra_data TEXT;",
    )
    d_sql_fe = layer.decide_delivery(msg_sql, "fe_worker", run_id=run_id)
    assert d_sql_fe["action"] == "drop"

    # 4. Pure CSS message is dropped for BE worker
    msg_css = FeedMessage(
        id="msg-4",
        timestamp="2026-10-24T12:00:03Z",
        sender=AgentSender.WORKER,
        lane=Lane.FE,
        type=MessageType.CHAT,
        content="Updating :root CSS vars: border-radius 8px and honey color scheme.",
    )
    d_css_be = layer.decide_delivery(msg_css, "be_worker", run_id=run_id)
    assert d_css_be["action"] == "drop"

    # 5. Raw debug traceback is summarized
    msg_debug = FeedMessage(
        id="msg-5",
        timestamp="2026-10-24T12:00:04Z",
        sender=AgentSender.WORKER,
        lane=Lane.BE,
        type=MessageType.CHAT,
        content="Traceback (most recent call last):\n  File 'main.py', line 12",
    )
    d_debug = layer.decide_delivery(msg_debug, "queen", run_id=run_id)
    assert d_debug["action"] == "summarize"


@pytest.mark.asyncio
async def test_delivery_decisions_persistence_and_stats(monkeypatch, tmp_path):
    run_id = "run-decision-persist"
    db_file = tmp_path / "decisions_persist.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))

    layer = RuleBasedDecisionLayer()

    msg_deliver = FeedMessage(
        id="msg-del-1",
        timestamp="2026-10-24T12:00:00Z",
        sender=AgentSender.QUEEN,
        type=MessageType.STATUS,
        content="Deliver this milestone update",
    )
    layer.decide_delivery(msg_deliver, "scribe", run_id=run_id)

    msg_drop = FeedMessage(
        id="msg-drop-1",
        timestamp="2026-10-24T12:00:01Z",
        sender=AgentSender.WORKER,
        type=MessageType.CHAT,
        content="DROP TABLE old_schema;",
    )
    layer.decide_delivery(msg_drop, "fe_worker", run_id=run_id)

    # Verify SQLite stats
    storage = get_storage()
    stats = storage.get_delivery_stats(run_id)
    assert stats["total"] == 2
    assert stats["delivered"] == 1
    assert stats["dropped"] == 1

    # Verify REST endpoint
    client = TestClient(app)
    resp = client.get(f"/runs/{run_id}/decisions/delivery")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["stats"]["total"] == 2


@pytest.mark.asyncio
async def test_jev_fallback_to_rules(monkeypatch, tmp_path):
    monkeypatch.setenv("JEV_API_KEY", "fake-jev-key")
    monkeypatch.setenv("JEV_API_URL", "http://127.0.0.1:9999/non-existent-jev")
    run_id = "run-jev-fallback"

    layer = RuleBasedDecisionLayer()
    msg = FeedMessage(
        id="msg-jev-1",
        timestamp="2026-10-24T12:00:00Z",
        sender=AgentSender.QUEEN,
        type=MessageType.STATUS,
        content="Checking fallback when Jev is offline",
    )
    # Must never raise an exception, must fall back cleanly to rules
    decision = layer.decide_delivery(msg, "scribe", run_id=run_id)
    assert decision["action"] == "deliver"
    assert decision["backend"] == "rules"


def test_whiteboard_filtering_confidence():
    layer = RuleBasedDecisionLayer()

    # Milestone status is high confidence
    msg_status = FeedMessage(
        id="msg-wf-1",
        timestamp="2026-10-24T12:00:00Z",
        sender=AgentSender.QUEEN,
        type=MessageType.STATUS,
        content="Frontend hero section completed and ready for preview.",
    )
    worthy, conf = layer.should_show_on_whiteboard(msg_status, return_confidence=True)
    assert worthy is True
    assert conf >= 0.8

    # Chit chat is low confidence
    msg_chat = FeedMessage(
        id="msg-wf-2",
        timestamp="2026-10-24T12:00:01Z",
        sender=AgentSender.WORKER,
        lane=Lane.FE,
        type=MessageType.CHAT,
        content="ok cool",
    )
    worthy2, conf2 = layer.should_show_on_whiteboard(msg_chat, return_confidence=True)
    assert worthy2 is False
    assert conf2 < 0.8
