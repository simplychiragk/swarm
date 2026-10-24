"""
Tests for Stage 13: The Gauntlet (Autonomous Multi-Persona Browser Testing Suite).
Validates parallel persona runs, strict permission URL restrictions,
whiteboard cards, SQLite artifact persistence, and HTML report generation.
"""

import os
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from sidecar.agents.gauntlet import GauntletRunner, gauntlet_runner, ACTIVE_PERSONAS, DROPPED_PERSONAS
from sidecar.agents.bus import MessageBus
from sidecar.models.contracts import WhiteboardCard, CardStatus, Lane
from sidecar.permissions import default_executor, resolve_safe_path
from sidecar.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_gauntlet_persona_execution(monkeypatch, tmp_path):
    run_id = f"run-gauntlet-{uuid.uuid4().hex[:6]}"
    db_file = tmp_path / "gauntlet.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))
    monkeypatch.setenv("SWARM_MODE", "mock")

    # Set up mock workspace
    workspace_dir = resolve_safe_path(run_id, ".")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    index_html = workspace_dir / "index.html"
    index_html.write_text("<!DOCTYPE html><html><body><h1>Waitlist</h1><input type='email'/><button id='submit-btn'>Join</button></body></html>", encoding="utf-8")

    bus = MessageBus(run_id=run_id)
    target_url = f"http://127.0.0.1:8000/runs/{run_id}/preview/"

    runner = GauntletRunner(concurrency_limit=2)
    report = await runner.run_gauntlet(target_url=target_url, run_id=run_id, bus=bus)

    # 1. Assertions on gauntlet return dictionary
    assert report["status"] == "success"
    assert report["run_id"] == run_id
    assert report["personas_tested"] == 4
    assert report["all_passed"] is True
    assert report["grade"] in ("A", "B")
    assert 1.0 <= report["average_friction"] <= 3.0

    # 2. Check each persona result
    res_list = report["results"]
    assert len(res_list) == 4
    persona_ids = {r["persona"] for r in res_list}
    assert persona_ids == {"impatient_mobile", "messy_input", "double_submit", "malformed_input"}

    for r in res_list:
        assert r["completed"] is True
        assert 1 <= r["friction_score"] <= 5
        assert r["provenance"] in ("real", "simulated")
        assert "latency_ms" in r

    # 3. Check Whiteboard cards
    from sidecar.storage import get_storage
    cards = get_storage().get_run_cards(run_id)
    card_ids = {c["id"] for c in cards}
    assert "card-gauntlet-impatient_mobile" in card_ids
    assert "card-gauntlet-messy_input" in card_ids
    assert "card-gauntlet-double_submit" in card_ids
    assert "card-gauntlet-malformed_input" in card_ids
    assert "card-gauntlet-summary" in card_ids

    # 4. Check HTML Report generated in workspace artifacts
    report_file = resolve_safe_path(run_id, "artifacts/gauntlet_report.html", must_exist=True)
    assert report_file.exists()
    html_text = report_file.read_text(encoding="utf-8")
    assert "Swarm Gauntlet Persona Audit Report" in html_text
    assert run_id in html_text
    assert "Architectural Notes & Dropped Personas" in html_text
    assert "Keyboard-Only User" in html_text

    # 5. Check SQLite artifact registration
    artifacts = get_storage().get_run_artifacts(run_id)
    assert any(a["name"] == "gauntlet_report.html" for a in artifacts)


@pytest.mark.asyncio
async def test_gauntlet_permission_enforcement(monkeypatch, tmp_path):
    """Verifies that the PolicyEngine hard-denies any Gauntlet URL outside the run's preview."""
    run_id = f"run-gauntlet-perm-{uuid.uuid4().hex[:6]}"
    db_file = tmp_path / "gauntlet_perm.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))

    from sidecar.permissions import default_executor
    engine = default_executor.policy_engine

    # Disallowed URL (not pointing to current run's preview)
    disallowed_url = "https://external-site.com/form"
    decision = engine.check(
        agent="gauntlet",
        tool="tinyfish_browser_task",
        args={"url": disallowed_url, "goal": "submit form"},
        context={"gauntlet": True, "persona": "impatient_mobile"},
        run_id=run_id,
    )

    assert decision.outcome == "deny"
    assert decision.tier == "FORBIDDEN"
    assert "Gauntlet violation" in decision.reason

    # Allowed URL (strictly points to current run's preview)
    allowed_url = f"http://127.0.0.1:8000/runs/{run_id}/preview/"
    decision_allowed = engine.check(
        agent="gauntlet",
        tool="tinyfish_browser_task",
        args={"url": allowed_url, "goal": "submit form"},
        context={"gauntlet": True, "persona": "impatient_mobile"},
        run_id=run_id,
    )

    assert decision_allowed.outcome == "allow" or decision_allowed.tier in ("LOW", "MEDIUM")
    assert decision_allowed.outcome != "deny"


def test_gauntlet_api_endpoints(monkeypatch, tmp_path):
    """Tests POST /runs/{run_id}/gauntlet and GET /runs/{run_id}/gauntlet/report."""
    run_id = f"run-gauntlet-api-{uuid.uuid4().hex[:6]}"
    db_file = tmp_path / "gauntlet_api.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))
    monkeypatch.setenv("SWARM_MODE", "mock")

    # Ensure workspace directory exists
    workspace_dir = resolve_safe_path(run_id, ".")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    index_html = workspace_dir / "index.html"
    index_html.write_text("<html><body>API Test</body></html>", encoding="utf-8")

    # 1. Trigger gauntlet
    resp = client.post(
        f"/runs/{run_id}/gauntlet",
        json={"url": f"http://127.0.0.1:8000/runs/{run_id}/preview/"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["personas_tested"] == 4
    assert "report_url" in data

    # 2. Retrieve HTML report endpoint
    resp_report = client.get(f"/runs/{run_id}/gauntlet/report")
    assert resp_report.status_code == 200
    assert "text/html" in resp_report.headers["content-type"]
    assert "Swarm Gauntlet" in resp_report.text
