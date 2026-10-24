"""
Versioned SQLite migrations for Swarm.
Uses a migrations table to record applied versions without any ORM.
"""

import sqlite3
import logging

logger = logging.getLogger("swarm.storage.migrations")

MIGRATIONS = [
    # Migration 1: Core tables
    """
    -- Runs table
    CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        goal TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        summary TEXT
    );

    -- Append-only events table with per-run sequence numbers
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        provenance TEXT NOT NULL DEFAULT 'real',
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
    CREATE INDEX IF NOT EXISTS idx_events_run_type ON events(run_id, event_type);

    -- Latest card state per card ID
    CREATE TABLE IF NOT EXISTS cards (
        id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        status TEXT NOT NULL,
        lane TEXT NOT NULL,
        evidence_json TEXT NOT NULL DEFAULT '[]',
        updated_at TEXT NOT NULL,
        PRIMARY KEY (run_id, id),
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    );

    -- Human approvals table
    CREATE TABLE IF NOT EXISTS approvals (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        card_id TEXT NOT NULL,
        prompt TEXT NOT NULL,
        options_json TEXT NOT NULL DEFAULT '[]',
        lane TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        decision TEXT,
        note TEXT,
        scope TEXT DEFAULT 'once',
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_approvals_run ON approvals(run_id);

    -- Artifacts registry (paths and metadata only, no blobs)
    CREATE TABLE IF NOT EXISTS artifacts (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        name TEXT NOT NULL,
        path TEXT NOT NULL,
        content_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id);

    -- LLM calls telemetry (no prompts, completions, or keys)
    CREATE TABLE IF NOT EXISTS llm_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        latency_ms REAL NOT NULL,
        status TEXT NOT NULL,
        error TEXT,
        timestamp TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_llm_calls_run ON llm_calls(run_id);

    -- Permission events table
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
    CREATE INDEX IF NOT EXISTS idx_perm_events_run ON permission_events(run_id);

    -- Decisions board table (agreed architectural & contract choices)
    CREATE TABLE IF NOT EXISTS decisions (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        summary TEXT NOT NULL,
        agreed_by_json TEXT NOT NULL DEFAULT '[]',
        thread_id TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_decisions_run ON decisions(run_id);

    -- Steers table (human steering commands & diffs)
    CREATE TABLE IF NOT EXISTS steers (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        mode TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        prompt TEXT NOT NULL,
        plan_diff_json TEXT,
        targets_json TEXT DEFAULT '[]',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_steers_run ON steers(run_id);

    -- Delivery decisions table (rules / Jev routing & filtering decisions)
    CREATE TABLE IF NOT EXISTS delivery_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        receiver TEXT NOT NULL,
        action TEXT NOT NULL,
        confidence REAL NOT NULL,
        backend TEXT NOT NULL,
        latency_ms REAL NOT NULL,
        timestamp TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_delivery_run ON delivery_decisions(run_id);

    -- Chat threads table
    CREATE TABLE IF NOT EXISTS threads (
        id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        subject TEXT NOT NULL,
        turn_count INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (run_id, id),
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_threads_run ON threads(run_id);
    """,
    # Migration 2: Align permission_events table schema
    """
    DROP TABLE IF EXISTS permission_events;
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
    CREATE INDEX IF NOT EXISTS idx_perm_events_run ON permission_events(run_id);
    """
]


def run_migrations(conn: sqlite3.Connection) -> None:
    """Applies all pending migrations within a transaction."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()

    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
    applied = {row[0] for row in cursor.fetchall()}

    for version, script in enumerate(MIGRATIONS, start=1):
        if version not in applied:
            logger.info(f"Applying SQLite migration version {version}...")
            cursor.executescript(script)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (?);", (version,))
            conn.commit()
            logger.info(f"SQLite migration version {version} applied successfully.")
