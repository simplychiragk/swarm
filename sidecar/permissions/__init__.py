"""
Swarm Permissions Package.
Provides centralized deterministic policy gating, secret redaction,
safe subprocess execution, path boundary sandboxing, and SQLite audit logging.
"""

from .redaction import redact, redact_data
from .path_safety import resolve_safe_path, get_run_workspace, PathSafetyError, get_repo_root
from .command_runner import run_safe_command, CommandResult
from .audit import record_permission_event, get_run_permission_events, clear_audit_db
from .policy import PolicyEngine, Decision
from .executor import ToolExecutor, ToolResult, default_executor, approval_coordinator

__all__ = [
    "redact",
    "redact_data",
    "resolve_safe_path",
    "get_run_workspace",
    "PathSafetyError",
    "get_repo_root",
    "run_safe_command",
    "CommandResult",
    "record_permission_event",
    "get_run_permission_events",
    "clear_audit_db",
    "PolicyEngine",
    "Decision",
    "ToolExecutor",
    "ToolResult",
    "default_executor",
    "approval_coordinator",
]
