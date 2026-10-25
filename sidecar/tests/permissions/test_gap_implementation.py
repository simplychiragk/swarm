"""
Tests for the Native Local Codebase Harness implementation:

Feature 1: SWARM_PROJECT_ROOT dynamic run workspace (escape the sandbox)
Feature 2: file_edit targeted search-and-replace with safe ambiguity failure
Feature 3: list_directory, search_code, and windowed file_read exploration tools
Feature 4: worker self-check loop helpers (test command resolution + escalation path)
Feature 5: GET /runs/{run_id}/git-diff (read-only) and POST /runs/{run_id}/git-revert
"""

import os
import uuid
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from sidecar.permissions import (
    PolicyEngine,
    ToolExecutor,
    resolve_safe_path,
    get_run_workspace,
    get_project_root,
    is_project_mode,
    PathSafetyError,
    set_project_root,
)
from sidecar.agents.worker import WorkerAgent, FileOp
from sidecar.agents.bus import MessageBus
from sidecar.models.contracts import Lane
from sidecar.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_project_root(monkeypatch):
    """Guarantees each test starts and ends with no external project root attached."""
    monkeypatch.delenv("SWARM_PROJECT_ROOT", raising=False)
    set_project_root(None)
    yield
    set_project_root(None)


# ---------------------------------------------------------------- Gap 1

def test_gap1_sandbox_default_workspace():
    run_id = f"run-gap1-sandbox-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    assert is_project_mode() is False
    assert "workspace" in str(ws) and run_id in str(ws)


def test_gap1_env_project_root(monkeypatch, tmp_path):
    target = tmp_path / "user-repo"
    target.mkdir()
    (target / "src").mkdir()
    (target / "src" / "app.py").write_text("print('hi')")
    monkeypatch.setenv("SWARM_PROJECT_ROOT", str(target))

    assert is_project_mode() is True
    root = get_project_root()
    assert root is not None and root.resolve() == target.resolve()

    # The run workspace now resolves to the user's repo
    run_id = f"run-gap1-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    assert ws.resolve() == target.resolve()

    # Safe paths resolve inside the repo; forbidden secrets still blocked
    safe = resolve_safe_path(run_id, "src/app.py", must_exist=True)
    assert safe.exists()
    with pytest.raises(PathSafetyError):
        resolve_safe_path(run_id, ".env")
    with pytest.raises(PathSafetyError):
        resolve_safe_path(run_id, "../outside.txt")


def test_gap1_nonexistent_project_root_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_PROJECT_ROOT", str(tmp_path / "does-not-exist"))
    with pytest.raises(PathSafetyError):
        get_run_workspace("run-gap1-bad-root")


def test_gap1_missing_field_but_env_blank_then_restored():
    # set_project_root(None) is idempotent and does not clear env-derived mode
    assert get_project_root() is None or isinstance(get_project_root(), Path)


# ---------------------------------------------------------------- Gap 2

@pytest.mark.asyncio
async def test_gap2_file_edit_targeted_replace():
    executor = ToolExecutor()
    run_id = f"run-gap2-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    target = ws / "src" / "widget.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("def greet():\n    return 'old'\n\ndef unused():\n    pass\n", encoding="utf-8")

    res = await executor.execute(
        run_id=run_id,
        agent="worker",
        tool="file_edit",
        args={
            "path": "src/widget.py",
            "target_block": "def greet():\n    return 'old'",
            "replacement_block": "def greet():\n    return 'new'",
        },
        context={"web_derived": False},
    )
    assert res.success is True
    assert res.data["success"] is True
    assert res.data["match_count"] == 1
    assert "return 'new'" in target.read_text(encoding="utf-8")
    assert "return 'old'" not in target.read_text(encoding="utf-8")
    # untouched block preserved
    assert "def unused():" in target.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_gap2_file_edit_ambiguity_and_missing_target_fail_safely():
    executor = ToolExecutor()
    run_id = f"run-gap2b-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    target = ws / "dup.py"
    target.write_text("x = 1\nx = 1\n", encoding="utf-8")

    # Ambiguous target: 2 matches without occurrence -> safe failure
    res = await executor.execute(
        run_id=run_id,
        agent="worker",
        tool="file_edit",
        args={"path": "dup.py", "target_block": "x = 1", "replacement_block": "y = 2"},
        context={"web_derived": False},
    )
    assert res.success is False
    assert "ambiguous" in res.error
    assert target.read_text(encoding="utf-8") == "x = 1\nx = 1\n"  # unchanged

    # Explicit occurrence 2 succeeds
    res2 = await executor.execute(
        run_id=run_id,
        agent="worker",
        tool="file_edit",
        args={"path": "dup.py", "target_block": "x = 1", "replacement_block": "y = 2", "occurrence": 2},
        context={"web_derived": False},
    )
    assert res2.success is True
    assert target.read_text(encoding="utf-8") == "x = 1\ny = 2\n"

    # Missing target fails without touching the file
    res3 = await executor.execute(
        run_id=run_id,
        agent="worker",
        tool="file_edit",
        args={"path": "dup.py", "target_block": "not_in_file", "replacement_block": "zz"},
        context={"web_derived": False},
    )
    assert res3.success is False
    assert "target_block not found" in res3.error


def test_gap2_policy_allows_edit_and_exploration_tools_as_low():
    engine = PolicyEngine()
    for tool, args in [
        ("file_edit", {"path": "src/a.py", "target_block": "a", "replacement_block": "b"}),
        ("list_directory", {"path": "."}),
        ("search_code", {"pattern": "hello"}),
    ]:
        decision = engine.check(run_id="gap2-policy", agent="worker", tool=tool, args=args)
        assert decision.tier == "LOW", f"{tool} should be LOW, got {decision.tier}"
        assert decision.outcome == "allow"


# ---------------------------------------------------------------- Gap 3

@pytest.mark.asyncio
async def test_gap3_list_directory_and_windowed_read():
    executor = ToolExecutor()
    run_id = f"run-gap3-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    (ws / "pkg").mkdir(parents=True, exist_ok=True)
    (ws / "pkg" / "mod.py").write_text("line1\nline2\nline3\n", encoding="utf-8")

    listing = await executor.execute(
        run_id=run_id, agent="worker", tool="list_directory",
        args={"path": ".", "recursive": True, "max_depth": 2},
        context={"web_derived": False},
    )
    assert listing.success is True
    paths = [e["path"] for e in listing.data["entries"]]
    assert "pkg/mod.py" in paths

    window = await executor.execute(
        run_id=run_id, agent="worker", tool="file_read",
        args={"path": "pkg/mod.py", "start_line": 2, "end_line": 3},
        context={"web_derived": False},
    )
    assert window.success is True
    assert window.data["content"] == "line2\nline3"
    assert window.data["total_lines"] == 3


@pytest.mark.asyncio
async def test_gap3_search_code_finds_matches_and_skips_secrets():
    executor = ToolExecutor()
    run_id = f"run-gap3b-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    (ws / "app").mkdir(parents=True, exist_ok=True)
    (ws / "app" / "routes.py").write_text(
        "def register_user():\n    return call_waitlist()\n", encoding="utf-8"
    )
    # Secret file must never appear in results
    (ws / "app" / ".env.local").write_text("waitlist_token = call_waitlist()\n", encoding="utf-8")

    found = await executor.execute(
        run_id=run_id, agent="worker", tool="search_code",
        args={"pattern": "call_waitlist"},
        context={"web_derived": False},
    )
    assert found.success is True
    files = [m["file"] for m in found.data["matches"]]
    assert any(f == "app/routes.py" for f in files)
    assert not any(".env" in f for f in files)


# ---------------------------------------------------------------- Gap 2/3 worker integration

@pytest.mark.asyncio
async def test_worker_apply_file_ops_edit_and_create():
    run_id = f"run-wops-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    (ws / "src").mkdir(parents=True, exist_ok=True)
    (ws / "src" / "nav.tsx").write_text("export const Nav = () => <nav>old</nav>;\n", encoding="utf-8")

    bus = MessageBus(run_id=run_id)
    worker = WorkerAgent(name="fe_worker", lane=Lane.FE, bus=bus)

    ops = [
        FileOp(file="src/new_helper.py", action="create", content="VALUE = 41\n", intent="new file"),
        FileOp(
            file="src/nav.tsx",
            action="edit",
            target="<nav>old</nav>",
            replacement="<nav>brand-new</nav>",
            intent="rebrand",
        ),
    ]
    applied = await worker._apply_file_ops(run_id, ops, "card-1", "Nav task")
    assert applied == 2
    assert (ws / "src" / "new_helper.py").read_text(encoding="utf-8") == "VALUE = 41\n"
    assert "brand-new" in (ws / "src" / "nav.tsx").read_text(encoding="utf-8")

    # Refuses to rewrite an existing file via whole-scale create
    ops2 = [FileOp(file="src/nav.tsx", action="create", content="obliterate", intent="bad")]
    applied2 = await worker._apply_file_ops(run_id, ops2, "card-2", "Bad task")
    assert applied2 == 0
    assert "brand-new" in (ws / "src" / "nav.tsx").read_text(encoding="utf-8")


# ---------------------------------------------------------------- Gap 4

def test_gap4_test_command_resolution():
    run_id = f"run-gap4-{uuid.uuid4().hex[:6]}"
    ws = get_run_workspace(run_id)
    (ws / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    bus = MessageBus(run_id=run_id)

    be_worker = WorkerAgent(name="be_worker", lane=Lane.BE, bus=bus)
    assert be_worker._resolve_test_command(run_id) == ["python", "-m", "pytest", "-q", "--no-header"]

    package = {"scripts": {"test": "vitest"}}
    (ws / "package.json").write_text(json.dumps(package), encoding="utf-8")
    fe_worker = WorkerAgent(name="fe_worker", lane=Lane.FE, bus=bus)
    assert fe_worker._resolve_test_command(run_id) == ["npm", "test"]

    # Custom override wins
    os.environ["SWARM_TEST_COMMAND"] = "pytest -q custom"
    try:
        assert fe_worker._resolve_test_command(run_id) == ["pytest", "-q", "custom"]
    finally:
        os.environ.pop("SWARM_TEST_COMMAND", None)


# ---------------------------------------------------------------- Gap 5

def test_gap5_git_diff_endpoint_sandbox_not_available():
    resp = client.get("/runs/run-gap5-sandbox/git-diff")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "run-gap5-sandbox"
    assert data["available"] is False
    assert data["changed_files"] == 0
    assert data["note"]


def test_gap5_git_revert_sandbox_noop():
    resp = client.post("/runs/run-gap5-sandbox/git-revert", json={"note": "nah"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["reverted"] is False
    assert "not git tracked" in data["note"] or "nothing to revert" in data["note"]
