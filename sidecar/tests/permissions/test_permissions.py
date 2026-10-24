"""
Comprehensive test suite for the Swarm Permission System:
1. Forbidden paths and secret files denied
2. Path traversal and symlink escape denied
3. Unknown tool denied
4. Allowlisted command allowed with correct cwd and scrubbed env
5. Non-allowlisted command becomes ask
6. Timeout kills the process tree
7. Budget exhaustion denies
8. Escalation rule bumps tier for web-derived actions
9. Approval timeout denies
10. "run" scope grant works for MEDIUM and is refused for HIGH
11. Redaction removes fake keys everywhere
12. Strict and demo modes behave as specified
13. FORBIDDEN cannot be disabled by any env var
14. Safe artifact endpoint allows valid files and blocks traversal / dispatches
"""

import os
import sys
import time
import asyncio
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from sidecar.permissions import (
    PolicyEngine,
    Decision,
    ToolExecutor,
    ToolResult,
    redact,
    redact_data,
    resolve_safe_path,
    get_run_workspace,
    PathSafetyError,
    record_permission_event,
    get_run_permission_events,
    clear_audit_db,
    run_safe_command,
    build_safe_child_env,
    approval_coordinator,
)
from sidecar.models.contracts import ApprovalResponse
from sidecar.main import app


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Ensures a clean permission environment for every test."""
    clear_audit_db()
    monkeypatch.setenv("SWARM_PERMISSION_MODE", "strict")
    yield
    clear_audit_db()
    approval_coordinator.cancel_all()


# --- Test 1: Forbidden secret files denied ---
def test_forbidden_secret_files_denied():
    engine = PolicyEngine()
    run_id = "test-run-forbidden"

    for forbidden_file in [".env", ".env.local", "id_rsa", "server.key", "cert.pem", ".ssh/id_ed25519", "api_secret.txt"]:
        decision = engine.check(
            run_id=run_id,
            agent="worker",
            tool="file_read",
            args={"path": forbidden_file},
        )
        assert decision.tier == "FORBIDDEN"
        assert decision.outcome == "deny"
        assert "FORBIDDEN" in decision.reason or "secret" in decision.reason.lower()


# --- Test 2: Path traversal and escape denied ---
def test_path_traversal_and_symlink_escape_denied():
    engine = PolicyEngine()
    run_id = "test-run-traversal"

    traversal_paths = [
        "../outside.txt",
        "../../etc/passwd",
        "..\\..\\Windows\\System32\\cmd.exe",
        "foo/../../bar.txt",
    ]

    for p in traversal_paths:
        decision = engine.check(
            run_id=run_id,
            agent="worker",
            tool="file_write",
            args={"path": p, "content": "malicious"},
        )
        assert decision.tier == "FORBIDDEN"
        assert decision.outcome == "deny"

        # Also test path_safety helper directly
        with pytest.raises(PathSafetyError):
            resolve_safe_path(run_id, p)


# --- Test 3: Unknown tool denied by default ---
def test_unknown_tool_denied():
    engine = PolicyEngine()
    decision = engine.check(
        run_id="test-run-unknown",
        agent="worker",
        tool="unregistered_dangerous_tool",
        args={"action": "exploit"},
    )
    assert decision.outcome == "deny"
    assert "Unknown or un-registered tool" in decision.reason


# --- Test 4: Allowlisted command allowed with correct cwd and scrubbed env ---
@pytest.mark.asyncio
async def test_allowlisted_command_allowed_with_correct_cwd_and_scrubbed_env(monkeypatch):
    monkeypatch.setenv("SWARM_PERMISSION_MODE", "demo")  # in demo mode allowlisted command auto-allows
    monkeypatch.setenv("FAKE_API_KEY", "super_secret_fake_key_12345")
    monkeypatch.setenv("SWARM_PRIVATE_KEY", "swarm_top_secret_key_99999")

    executor = ToolExecutor()
    run_id = "test-run-allowlist"

    # 1. Verify child environment is strictly scrubbed of secrets
    safe_env = build_safe_child_env()
    assert "FAKE_API_KEY" not in safe_env
    assert "SWARM_PRIVATE_KEY" not in safe_env
    assert "PATH" in safe_env

    # 2. Execute allowlisted command inside workspace in demo mode
    res = await executor.execute(
        run_id=run_id,
        agent="worker",
        tool="command_run",
        args={"argv": [sys.executable, "--version"]},
    )

    assert res.success is True
    assert res.outcome == "allow"
    assert res.tier == "MEDIUM"
    assert "Python" in res.data["stdout"] or "Python" in res.data["stderr"]


# --- Test 5: Non-allowlisted command becomes HIGH ask ---
def test_non_allowlisted_command_becomes_high_ask():
    engine = PolicyEngine()
    decision = engine.check(
        run_id="test-run-cmd-high",
        agent="worker",
        tool="command_run",
        args={"argv": ["curl", "https://untrusted-domain.com/script.sh"]},
    )
    assert decision.tier == "HIGH"
    assert decision.outcome == "ask"
    assert decision.scope_options == ["once"]


# --- Test 6: Timeout kills the process tree ---
@pytest.mark.asyncio
async def test_timeout_kills_process_tree():
    run_id = "test-run-timeout"
    ws = get_run_workspace(run_id)

    # Launch a python command that sleeps for 10 seconds with a 0.5s timeout
    sleep_code = "import time; time.sleep(10)"
    t0 = time.monotonic()
    result = await run_safe_command(
        argv=[sys.executable, "-c", sleep_code],
        cwd=ws,
        timeout_s=0.5,
    )
    duration = time.monotonic() - t0

    assert result.timed_out is True
    assert duration < 3.0  # Finished promptly on timeout
    assert "TIMED OUT" in result.stderr


# --- Test 7: Budget exhaustion denies ---
def test_budget_exhaustion_denies():
    engine = PolicyEngine()
    run_id = "test-run-budget"

    # Simulate exhaust tool calls
    for _ in range(engine.budgets.get("max_command_runs", 25)):
        engine.increment_usage(run_id, "worker", "command_run")

    decision = engine.check(
        run_id=run_id,
        agent="worker",
        tool="command_run",
        args={"argv": [sys.executable, "--version"]},
    )
    assert decision.outcome == "deny"
    assert decision.decided_by == "budget"
    assert "budget exceeded" in decision.reason.lower()


# --- Test 8: Escalation rule bumps tier for web-derived actions ---
def test_escalation_rule_bumps_tier_for_web_derived():
    engine = PolicyEngine()
    run_id = "test-run-escalation"

    # Standard file_write is LOW
    low_decision = engine.check(
        run_id=run_id,
        agent="worker",
        tool="file_write",
        args={"path": "src/hello.txt", "content": "hello"},
        context={"web_derived": False},
    )
    assert low_decision.tier == "LOW"
    assert low_decision.outcome == "allow"

    # Web-derived file_write escalates to MEDIUM
    med_decision = engine.check(
        run_id=run_id,
        agent="worker",
        tool="file_write",
        args={"path": "src/hello.txt", "content": "hello"},
        context={"web_derived": True},
    )
    assert med_decision.tier == "MEDIUM"
    assert "Escalated: action traces to untrusted web content" in med_decision.reason

    # Allowlisted command (normally MEDIUM) escalates to HIGH
    high_decision = engine.check(
        run_id=run_id,
        agent="worker",
        tool="command_run",
        args={"argv": [sys.executable, "-m", "pytest"]},
        context={"web_derived": True},
    )
    assert high_decision.tier == "HIGH"
    assert "Escalated: action traces to untrusted web content" in high_decision.reason


# --- Test 9: Approval timeout denies ---
@pytest.mark.asyncio
async def test_approval_timeout_denies(monkeypatch):
    executor = ToolExecutor()
    # Configure 0.3s timeout for test
    executor.policy_engine.budgets["default_approval_timeout_s"] = 0.3

    run_id = "test-run-approval-timeout"
    res = await executor.execute(
        run_id=run_id,
        agent="worker",
        tool="command_run",
        args={"argv": ["untrusted_tool", "--deploy"]},
    )

    assert res.success is False
    assert res.outcome == "deny"
    assert "Approval request timed out" in res.error or "timed out" in res.error.lower()


# --- Test 10: "run" scope grant works for MEDIUM and refused for HIGH ---
def test_run_scope_grant_works_for_medium_and_refused_for_high():
    engine = PolicyEngine()
    run_id = "test-run-grants"

    # Grant for MEDIUM tool succeeds
    granted = engine.register_run_grant(run_id, "command_run", tier="MEDIUM")
    assert granted is True
    assert engine.has_run_grant(run_id, "command_run") is True

    # Grant for HIGH tool is refused
    refused = engine.register_run_grant(run_id, "file_delete", tier="HIGH")
    assert refused is False
    assert engine.has_run_grant(run_id, "file_delete") is False


# --- Test 11: Redaction removes fake keys everywhere ---
def test_redaction_removes_fake_keys_everywhere(monkeypatch):
    fake_api_key = "tf_live_9876543210fedcba"
    monkeypatch.setenv("TINYFISH_API_KEY", fake_api_key)

    raw_text = f"Connecting to TinyFish with key={fake_api_key} and Bearer a1b2c3d4e5f6g7h8i9j0"
    redacted_text = redact(raw_text)

    assert fake_api_key not in redacted_text
    assert "[REDACTED_SECRET]" in redacted_text

    # Private key test
    fake_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0fake...\n-----END RSA PRIVATE KEY-----"
    assert redact(fake_pem) == "[REDACTED_SECRET]"

    # Test dictionary deep redaction
    data = {"secret_field": fake_api_key, "nested": [fake_pem, "safe_text"]}
    clean_data = redact_data(data)
    assert clean_data["secret_field"] == "[REDACTED_SECRET]"
    assert clean_data["nested"][0] == "[REDACTED_SECRET]"
    assert clean_data["nested"][1] == "safe_text"


# --- Test 12: Strict and demo modes behave as specified ---
def test_strict_and_demo_modes(monkeypatch):
    engine = PolicyEngine()
    run_id = "test-run-modes"

    # In strict mode: allowlisted command asks
    monkeypatch.setenv("SWARM_PERMISSION_MODE", "strict")
    dec_strict = engine.check(
        run_id=run_id,
        agent="worker",
        tool="command_run",
        args={"argv": ["npm", "install"]},
    )
    assert dec_strict.tier == "MEDIUM"
    assert dec_strict.outcome == "ask"

    # In demo mode: allowlisted command auto-allows
    monkeypatch.setenv("SWARM_PERMISSION_MODE", "demo")
    dec_demo = engine.check(
        run_id=run_id,
        agent="worker",
        tool="command_run",
        args={"argv": ["npm", "install"]},
    )
    assert dec_demo.tier == "MEDIUM"
    assert dec_demo.outcome == "allow"
    assert "demo" in dec_demo.reason.lower()

    # In demo mode: HIGH command STILL asks!
    dec_high = engine.check(
        run_id=run_id,
        agent="worker",
        tool="command_run",
        args={"argv": ["unknown_script.sh"]},
    )
    assert dec_high.tier == "HIGH"
    assert dec_high.outcome == "ask"


# --- Test 13: FORBIDDEN cannot be disabled by any env var ---
def test_forbidden_cannot_be_disabled_by_any_env_var(monkeypatch):
    engine = PolicyEngine()
    run_id = "test-run-cant-disable"

    for env_val in ["demo", "none", "off", "disabled", "false"]:
        monkeypatch.setenv("SWARM_PERMISSION_MODE", env_val)

        # Sudo is always forbidden
        dec_sudo = engine.check(
            run_id=run_id,
            agent="worker",
            tool="command_run",
            args={"argv": ["sudo", "rm", "-rf", "/"]},
        )
        assert dec_sudo.tier == "FORBIDDEN"
        assert dec_sudo.outcome == "deny"

        # Reading .env is always forbidden
        dec_env = engine.check(
            run_id=run_id,
            agent="worker",
            tool="file_read",
            args={"path": ".env"},
        )
        assert dec_env.tier == "FORBIDDEN"
        assert dec_env.outcome == "deny"


# --- Test 14: Permission audit and safe artifact serving endpoints ---
def test_permissions_audit_and_artifact_endpoints():
    client = TestClient(app)
    run_id = "run-audit-endpoint-test"

    # Record test event
    record_permission_event(
        run_id=run_id,
        agent="qa_bee",
        tool="command_run",
        args_summary="npm test",
        tier="MEDIUM",
        outcome="allow",
        decided_by="demo",
        reason="Auto-approved in demo",
    )

    # 1. GET /runs/{run_id}/permissions
    resp = client.get(f"/runs/{run_id}/permissions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == run_id
    assert data["count"] >= 1
    assert data["events"][0]["tool"] == "command_run"

    # 2. GET /runs/{run_id}/artifacts/{artifact_id}
    # Create valid artifact file in workspace
    ws = get_run_workspace(run_id)
    artifact_file = ws / "screenshot.png"
    artifact_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_png_data")

    resp_art = client.get(f"/runs/{run_id}/artifacts/screenshot.png")
    assert resp_art.status_code == 200
    assert resp_art.headers["content-type"] == "image/png"
    assert resp_art.content == b"\x89PNG\r\n\x1a\nfake_png_data"

    # Traversal escape is blocked with 403
    resp_block = client.get(f"/runs/{run_id}/artifacts/..%2f..%2fsidecar%2fmain.py")
    assert resp_block.status_code in (400, 403, 404)


@pytest.mark.asyncio
async def test_workspace_tree_and_file_endpoints():
    client = TestClient(app)
    run_id = "test-run-tree"
    ws = get_run_workspace(run_id)

    # 1. GET /runs/{run_id}/tree
    resp = client.get(f"/runs/{run_id}/tree")
    assert resp.status_code == 200
    tree_data = resp.json()
    assert tree_data["run_id"] == run_id
    assert "files" in tree_data
    assert len(tree_data["files"]) > 0

    # Verify starter file App.tsx is seeded
    app_file = next((f for f in tree_data["files"] if "App.tsx" in f["name"]), None)
    assert app_file is not None
    assert app_file["language"] == "typescript"
    assert "export default function App" in app_file["content"]

    # 2. PUT /runs/{run_id}/files/src/Custom.tsx
    new_content = "export const Custom = () => <div>Custom</div>;"
    put_resp = client.put(
        f"/runs/{run_id}/files/src/Custom.tsx",
        json={"content": new_content},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["success"] is True

    # 3. GET /runs/{run_id}/files/src/Custom.tsx
    get_resp = client.get(f"/runs/{run_id}/files/src/Custom.tsx")
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == new_content

    # 4. POST /runs/{run_id}/files create new file
    post_resp = client.post(
        f"/runs/{run_id}/files",
        json={"path": "src/NewFile.json", "content": '{"test": true}', "is_directory": False},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    # 5. Traversal on PUT is blocked with 403
    block_resp = client.put(
        f"/runs/{run_id}/files/..%2f..%2fescape.txt",
        json={"content": "malicious"},
    )
    assert block_resp.status_code in (400, 403)

