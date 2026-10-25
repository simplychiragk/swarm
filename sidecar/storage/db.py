"""
Database connection manager and lifecycle for SQLite.
Configures WAL mode, busy timeouts, and executes versioned migrations.
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional
from .migrations import run_migrations


def get_default_db_path() -> Path:
    """Returns Path to the configured SQLite database, defaulting to data/swarm.db."""
    custom = os.environ.get("SWARM_DB_PATH", "").strip()
    if custom:
        return Path(custom).resolve()
    repo_root = Path(__file__).resolve().parent.parent.parent
    return (repo_root / "data" / "swarm.db").resolve()


class Database:
    """Thread-safe SQLite connection wrapper with WAL mode and auto-migrations."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_connection()

    def _init_connection(self) -> None:
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=10.0,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._conn.execute("PRAGMA synchronous = NORMAL;")
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA busy_timeout = 5000;")
        self._conn.commit()
        run_migrations(self._conn)

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._init_connection()
        return self._conn  # type: ignore

    def execute_write(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self.connection.cursor()
            cur.execute(query, params)
            self.connection.commit()
            return cur

    def execute_read(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.connection.cursor()
        cur.execute(query, params)
        return cur

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None


_global_db: Optional[Database] = None
_db_init_lock = threading.Lock()


def get_db(db_path: Optional[Path] = None) -> Database:
    global _global_db
    with _db_init_lock:
        if _global_db is None or (db_path and _global_db.db_path != db_path):
            _global_db = Database(db_path)
        return _global_db
