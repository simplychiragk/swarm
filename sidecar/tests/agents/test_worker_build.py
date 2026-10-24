"""
Unit tests for Stage 6: Workers build real project, sidecar serves it, seeded-bug mode.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sidecar.agents.worker import WorkerAgent
from sidecar.agents.bus import MessageBus
from sidecar.models.contracts import Lane
from sidecar.permissions import resolve_safe_path
from sidecar.main import app


@pytest.fixture
def run_id():
    return "test-run-build-6"


@pytest.mark.asyncio
async def test_workers_write_real_landing_page_files(run_id):
    """Verify FE and BE workers write real functioning files into workspace/<run_id>/."""
    bus = MessageBus(run_id=run_id)
    be_worker = WorkerAgent("be_worker", Lane.BE, bus)
    fe_worker = WorkerAgent("fe_worker", Lane.FE, bus)

    # BE worker writes API route
    await be_worker.execute_task(
        task_id="task-be-1",
        title="FastAPI Waitlist Route",
        description="Write /api/waitlist endpoint",
        run_id=run_id,
    )

    # FE worker writes HTML, CSS, JS
    await fe_worker.execute_task(
        task_id="task-fe-1",
        title="Landing Page",
        description="Write index.html, style.css, app.js",
        run_id=run_id,
    )

    # Verify real files exist in workspace/<run_id>/
    html_file = resolve_safe_path(run_id, "index.html", must_exist=True)
    css_file = resolve_safe_path(run_id, "style.css", must_exist=True)
    js_file = resolve_safe_path(run_id, "app.js", must_exist=True)
    api_file = resolve_safe_path(run_id, "api/main.py", must_exist=True)

    assert "<!doctype html>" in html_file.read_text(encoding="utf-8")
    assert "--honey" in css_file.read_text(encoding="utf-8")
    assert "addEventListener" in js_file.read_text(encoding="utf-8")
    assert "/api/waitlist" in api_file.read_text(encoding="utf-8")


def test_preview_serving_and_waitlist_api(run_id):
    """Verify sidecar serves the built landing page and waitlist submission endpoint."""
    client = TestClient(app)

    # 1. Preview index.html
    res_preview = client.get(f"/runs/{run_id}/preview/")
    assert res_preview.status_code == 200
    assert "text/html" in res_preview.headers["content-type"]
    assert "Join the Waitlist" in res_preview.text

    # 2. Preview style.css
    res_css = client.get(f"/runs/{run_id}/preview/style.css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.headers["content-type"]

    # 3. Test waitlist submission endpoint
    res_post = client.post(
        f"/runs/{run_id}/api/waitlist",
        json={"name": "Alex", "email": "alex@example.com", "role": "Engineer"},
    )
    assert res_post.status_code == 201
    body = res_post.json()
    assert body["status"] == "success"
    assert body["queue_position"] == 42


@pytest.mark.asyncio
async def test_seeded_bug_mode_introduces_disabled_button():
    """Verify SWARM_DEMO_MODE=seeded_bug introduces disabled button into index.html."""
    old_mode = os.environ.get("SWARM_DEMO_MODE")
    os.environ["SWARM_DEMO_MODE"] = "seeded_bug"
    test_bug_run = "test-run-seeded-bug"

    try:
        bus = MessageBus(run_id=test_bug_run)
        fe_worker = WorkerAgent("fe_worker", Lane.FE, bus)
        await fe_worker.execute_task(
            task_id="task-fe-bug",
            title="Landing with seeded bug",
            description="Build hero",
            run_id=test_bug_run,
        )

        html_file = resolve_safe_path(test_bug_run, "index.html", must_exist=True)
        content = html_file.read_text(encoding="utf-8")
        assert 'id="submit-btn" disabled' in content or ('submit-btn' in content and 'disabled' in content)

        # Now test apply_fix removes the bug
        await fe_worker.apply_fix(run_id=test_bug_run)
        content_fixed = html_file.read_text(encoding="utf-8")
        assert 'id="submit-btn" disabled' not in content_fixed
    finally:
        if old_mode is None:
            os.environ.pop("SWARM_DEMO_MODE", None)
        else:
            os.environ["SWARM_DEMO_MODE"] = old_mode
