"""
Unit tests for SQLite storage, migrations, state projections, and replay.
"""

import os
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from sidecar.storage.db import Database
from sidecar.storage.service import StorageService
from sidecar.storage.migrations import run_migrations
from sidecar.main import app
from sidecar.broadcaster import broadcaster


@pytest.fixture
def temp_db():
    """Provides a fresh isolated SQLite database in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_swarm.db"
        db = Database(db_path=db_path)
        yield db
        if db._conn:
            db._conn.close()


@pytest.fixture
def storage(temp_db):
    """Provides a StorageService backed by the temp database."""
    return StorageService(db=temp_db)


def test_migrations_and_tables(temp_db):
    """Verifies that all migrations apply cleanly and core tables are created."""
    conn = temp_db.connection
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}

    expected_tables = {
        "schema_migrations",
        "runs",
        "events",
        "cards",
        "approvals",
        "artifacts",
        "llm_calls",
        "permission_events",
        "decisions",
        "steers",
        "delivery_decisions",
        "threads",
    }
    for t in expected_tables:
        assert t in tables, f"Expected table '{t}' was not found in database"


def test_event_ordering_and_sequential_seq(storage):
    """Verifies per-run sequential sequence numbering and chronological retrieval."""
    run_id = "test-run-ordering"
    storage.ensure_run(run_id, goal="Test event sequence")

    seq1 = storage.record_event(run_id, "feed_message", {"content": "First event"}, provenance="real")
    seq2 = storage.record_event(run_id, "feed_message", {"content": "Second event"}, provenance="real")
    seq3 = storage.record_event(run_id, "feed_message", {"content": "Third event"}, provenance="simulated")

    assert seq1 == 1
    assert seq2 == 2
    assert seq3 == 3

    events = storage.get_run_events(run_id)
    assert len(events) == 3
    assert [e["seq"] for e in events] == [1, 2, 3]
    assert events[0]["payload"]["content"] == "First event"
    assert events[1]["payload"]["content"] == "Second event"
    assert events[2]["provenance"] == "simulated"


def test_after_seq_filtering(storage):
    """Verifies that after_seq properly queries only delta events."""
    run_id = "test-run-delta"
    for i in range(1, 6):
        storage.record_event(run_id, "feed_message", {"step": i})

    all_events = storage.get_run_events(run_id)
    assert len(all_events) == 5

    delta = storage.get_run_events(run_id, after_seq=3)
    assert len(delta) == 2
    assert [e["seq"] for e in delta] == [4, 5]


def test_latest_card_state_projection(storage):
    """Verifies that card_upsert events project into the cards table with latest state."""
    run_id = "test-run-cards"
    card_id = "card-api-spec"

    # 1. Initial planned state
    storage.record_event(
        run_id,
        "card_upsert",
        {
            "id": card_id,
            "title": "API Specification",
            "summary": "Drafting waitlist endpoints",
            "status": "planned",
            "lane": "BE",
            "evidence": [],
        },
    )

    cards = storage.get_run_cards(run_id)
    assert len(cards) == 1
    assert cards[0]["id"] == card_id
    assert cards[0]["status"] == "planned"

    # 2. In progress update
    storage.record_event(
        run_id,
        "card_upsert",
        {
            "id": card_id,
            "title": "API Specification",
            "summary": "Implementing FastAPI handlers",
            "status": "in_progress",
            "lane": "BE",
            "evidence": [{"kind": "diff", "url_or_text": "+ /api/waitlist"}],
        },
    )

    cards = storage.get_run_cards(run_id)
    assert len(cards) == 1
    assert cards[0]["status"] == "in_progress"
    assert len(cards[0]["evidence"]) == 1
    assert cards[0]["evidence"][0]["kind"] == "diff"


def test_approval_lifecycle_and_projection(storage):
    """Verifies that approval_request and approval_response project state correctly."""
    run_id = "test-run-approvals"
    appr_id = "appr-deploy-1"
    card_id = "card-deploy"

    # Create initial card
    storage.record_event(
        run_id,
        "card_upsert",
        {
            "id": card_id,
            "title": "Deploy Landing Page",
            "summary": "Ready for production release",
            "status": "needs_approval",
            "lane": "Ops",
        },
    )

    # Emit approval_request
    storage.record_event(
        run_id,
        "approval_request",
        {
            "id": appr_id,
            "card_id": card_id,
            "prompt": "Approve release to staging?",
            "options": ["approve", "redirect"],
            "lane": "Ops",
        },
    )

    pending = storage.get_pending_approvals(run_id)
    assert len(pending) == 1
    assert pending[0]["id"] == appr_id
    assert pending[0]["status"] == "pending"

    # Emit approval_response (approve)
    storage.record_event(
        run_id,
        "approval_response",
        {
            "approval_id": appr_id,
            "card_id": card_id,
            "decision": "approve",
            "note": "Looks great to release",
            "scope": "once",
        },
    )

    # Pending approvals should now be empty
    assert len(storage.get_pending_approvals(run_id)) == 0

    # Card status should automatically transition to 'done'
    cards = storage.get_run_cards(run_id)
    assert len(cards) == 1
    assert cards[0]["status"] == "done"


def test_replay_endpoint_and_rest_api():
    """Verifies REST endpoints /runs, /runs/{id}/events, and /runs/{id}/replay."""
    client = TestClient(app)

    # 1. Check list runs
    res = client.get("/runs")
    assert res.status_code == 200
    assert "runs" in res.json()

    # 2. Record an event via mock runner or storage
    from sidecar.storage import get_storage
    storage = get_storage()
    test_run_id = "run-replay-test"
    storage.ensure_run(test_run_id, goal="Replay test goal")
    storage.record_event(test_run_id, "feed_message", {"content": "Replay msg 1"})
    storage.record_event(test_run_id, "feed_message", {"content": "Replay msg 2"})

    # 3. Check /runs/{id}
    res_run = client.get(f"/runs/{test_run_id}")
    assert res_run.status_code == 200
    assert res_run.json()["id"] == test_run_id

    # 4. Check /runs/{id}/events
    res_events = client.get(f"/runs/{test_run_id}/events")
    assert res_events.status_code == 200
    data = res_events.json()
    assert data["count"] >= 2
    assert data["events"][0]["payload"]["content"] == "Replay msg 1"

    # 5. Check /runs/{id}/replay
    res_replay = client.post(f"/runs/{test_run_id}/replay", json={"speed": 0})
    assert res_replay.status_code == 200
    assert res_replay.json()["status"] == "replaying"
    assert res_replay.json()["event_count"] >= 2
