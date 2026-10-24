"""
SQLite Audit Persistence for Swarm Permissions.
Stores all policy checks, user approvals, timeouts, and denials in
the permission_events table.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from .redaction import redact


def get_db_path() -> Path:
    """Returns the configured or default SQLite audit database path."""
    custom_path = os.environ.get("SWARM_DB_PATH")
    if custom_path:
        p = Path(custom_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # Default to repo_root/workspace/audit.db
    from .path_safety import get_repo_root
    default_p = (get_repo_root() / "workspace" / "audit.db").resolve()
    default_p.parent.mkdir(parents=True, exist_ok=True)
    return default_p


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Creates a connection and ensures schema exists."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS permission_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                tool TEXT NOT NULL,
                args_summary TEXT NOT NULL,
                tier TEXT NOT NULL,
                outcome TEXT NOT NULL,
                decided_by TEXT NOT NULL,
                reason TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perm_run_id ON permission_events(run_id);")
    return conn


def record_permission_event(
    run_id: str,
    agent: str,
    tool: str,
    args_summary: str,
    tier: str,
    outcome: str,
    decided_by: str,
    reason: str,
    timestamp: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """
    Records a permission check result in SQLite.
    Automatically redacts args_summary and reason before saving.
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    clean_args = redact(args_summary)
    clean_reason = redact(reason)

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO permission_events (
                    run_id, timestamp, agent, tool, args_summary, tier, outcome, decided_by, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, ts, agent, tool, clean_args, tier, outcome, decided_by, clean_reason),
            )
            return cursor.lastrowid or 0
    finally:
        conn.close()


def get_run_permission_events(run_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all permission audit records for a run.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT id, run_id, timestamp, agent, tool, args_summary, tier, outcome, decided_by, reason
            FROM permission_events
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def clear_audit_db(db_path: Optional[Path] = None) -> None:
    """Clears all records in the audit database (useful in tests/reset)."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM permission_events;")
    finally:
        conn.close()
