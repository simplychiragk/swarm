# Sidecar Permissions Package

The `sidecar.permissions` package is Swarm's centralized security boundary and execution policy engine.

## Core Purpose

In Swarm, agents are not permitted to invoke tools directly. Every tool invocation passes through `ToolExecutor`, which consults `PolicyEngine` before taking any action.

```
Agent -> ToolExecutor.execute(tool, args, context)
            |
            +--> PolicyEngine.check() [Deterministic Policy + Jev Advice]
            |       |
            |       +--> FORBIDDEN: Deny immediately
            |       +--> HIGH: Require interactive user approval
            |       +--> MEDIUM: Check strict/demo mode & active run grants
            |       +--> LOW: Auto-allow
            |
            +--> Safe Execution (path_safety / command_runner / handlers)
            |
            +--> Redaction Engine (scrub all stdout/stderr/results)
            |
            +--> SQLite Audit Trail (record_permission_event)
```

## Module Structure

| Module | Responsibility |
|---|---|
| `policy.json` | Deterministic configuration of tiers, allowlisted binaries, subcommands, and budgets. Protected from agent writes. |
| `policy.py` | `PolicyEngine` evaluating tool requests against `policy.json`, budget counters, escalation rules, and `SWARM_PERMISSION_MODE`. |
| `executor.py` | `ToolExecutor` and `ApprovalCoordinator` orchestrating tool execution, suspension for user approval, and audit dispatch. |
| `command_runner.py` | `run_safe_command()` executing argv lists (no `shell=True`), minimal sanitized environment, timeout termination with process-tree cleanup. |
| `path_safety.py` | `resolve_safe_path()` locking file operations inside `workspace/<run_id>/` with traversal and secret guards. |
| `redaction.py` | `redact()` and `redact_data()` stripping API keys, tokens, and ambient environment secrets. |
| `audit.py` | SQLite audit logger recording all tool checks, outcomes, execution durations, and approvals. |

## Quick Usage

```python
from sidecar.permissions import default_executor, ToolResult

# Safely write a file to a run's workspace
result: ToolResult = await default_executor.execute(
    agent="worker_fe",
    tool="file_write",
    args={"path": "src/App.tsx", "content": "export default function App() {}"},
    context={"run_id": "run-123"}
)

if not result.success:
    print(f"Action blocked: {result.error}")
```

## Testing

Run the dedicated 14-point test suite:
```powershell
pytest sidecar/tests/permissions -v
```
