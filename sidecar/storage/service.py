"""
High-level storage service providing transactional operations for Swarm entities.
Enforces single write-point event logging, card caching, and telemetry recording.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from .db import Database, get_db

logger = logging.getLogger("swarm.storage.service")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StorageService:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    # --- Runs Management ---
    def ensure_run(
        self,
        run_id: str,
        goal: str = "Build a landing page with a waitlist form",
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ensures a run record exists, creating it if missing."""
        t = now_iso()
        self.db.execute_write(
            """
            INSERT INTO runs (id, goal, status, created_at, updated_at, summary)
            VALUES (?, ?, 'active', ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at;
            """,
            (run_id, goal, t, t, summary),
        )
        return self.get_run(run_id)  # type: ignore

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        cur = self.db.execute_read("SELECT * FROM runs WHERE id = ?;", (run_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?;", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]

    def update_run_status(self, run_id: str, status: str, summary: Optional[str] = None) -> None:
        t = now_iso()
        completed = t if status in ("completed", "failed", "cancelled") else None
        self.db.execute_write(
            """
            UPDATE runs
            SET status = ?, updated_at = ?, completed_at = COALESCE(?, completed_at), summary = COALESCE(?, summary)
            WHERE id = ?;
            """,
            (status, t, completed, summary, run_id),
        )

    # --- Events Logging & State Projection ---
    def record_event(
        self,
        run_id: str,
        event_type: str,
        payload: Dict[str, Any],
        provenance: str = "real",
    ) -> int:
        """
        Single write point for inbound and outbound events.
        Allocates sequential per-run seq and projections cards and approvals automatically.
        """
        try:
            self.ensure_run(run_id)
            t = now_iso()

            with self.db._lock:
                conn = self.db.connection
                # Allocate next per-run sequence number atomically
                cur = conn.cursor()
                cur.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?;",
                    (run_id,),
                )
                seq: int = cur.fetchone()[0]

                # 1. Insert into append-only events table
                payload_str = json.dumps(payload)
                cur.execute(
                    """
                    INSERT INTO events (run_id, seq, event_type, payload_json, timestamp, provenance)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (run_id, seq, event_type, payload_str, t, provenance),
                )

                # 2. State projection: Card Upserts
                if event_type == "card_upsert":
                    card_id = payload.get("id", "")
                    title = payload.get("title", "")
                    summary = payload.get("summary", "")
                    status = payload.get("status", "planned")
                    lane = payload.get("lane", "none")
                    evidence = json.dumps(payload.get("evidence", []))
                    card_time = payload.get("updated_at") or t

                    cur.execute(
                        """
                        INSERT INTO cards (id, run_id, title, summary, status, lane, evidence_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(run_id, id) DO UPDATE SET
                            title = excluded.title,
                            summary = excluded.summary,
                            status = excluded.status,
                            lane = excluded.lane,
                            evidence_json = excluded.evidence_json,
                            updated_at = excluded.updated_at;
                        """,
                        (card_id, run_id, title, summary, status, lane, evidence, card_time),
                    )

                # 3. State projection: Approval Requests
                elif event_type == "approval_request":
                    appr_id = payload.get("id", "")
                    card_id = payload.get("card_id", "")
                    prompt = payload.get("prompt", "")
                    options = json.dumps(payload.get("options", []))
                    lane = payload.get("lane", "none")
                    req_time = payload.get("created_at") or t

                    cur.execute(
                        """
                        INSERT INTO approvals (id, run_id, card_id, prompt, options_json, lane, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                        ON CONFLICT(id) DO UPDATE SET
                            prompt = excluded.prompt,
                            options_json = excluded.options_json;
                        """,
                        (appr_id, run_id, card_id, prompt, options, lane, req_time),
                    )

                # 4. State projection: Approval Responses
                elif event_type == "approval_response":
                    appr_id = payload.get("approval_id", "")
                    card_id = payload.get("card_id", "")
                    decision = payload.get("decision", "approve")
                    note = payload.get("note", "")
                    scope = payload.get("scope", "once")

                    cur.execute(
                        """
                        UPDATE approvals
                        SET status = 'resolved', decision = ?, note = ?, scope = ?, resolved_at = ?
                        WHERE id = ?;
                        """,
                        (decision, note, scope, t, appr_id),
                    )
                    # Also update latest card status
                    card_status = "done" if decision == "approve" else "failed"
                    cur.execute(
                        """
                        UPDATE cards
                        SET status = ?, updated_at = ?
                        WHERE run_id = ? AND id = ?;
                        """,
                        (card_status, t, run_id, card_id),
                    )

                conn.commit()
                return seq

        except Exception as e:
            # Storage write failures are logged and must NEVER crash live streaming
            logger.error(f"Failed to record event to SQLite: {e}", exc_info=True)
            return -1

    def get_run_events(self, run_id: str, after_seq: int = 0) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            """
            SELECT * FROM events
            WHERE run_id = ? AND seq > ?
            ORDER BY seq ASC;
            """,
            (run_id, after_seq),
        )
        events = []
        for row in cur.fetchall():
            item = dict(row)
            try:
                item["payload"] = json.loads(item["payload_json"])
            except Exception:
                item["payload"] = {}
            events.append(item)
        return events

    def get_run_cards(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM cards WHERE run_id = ? ORDER BY updated_at ASC;",
            (run_id,),
        )
        cards = []
        for row in cur.fetchall():
            item = dict(row)
            try:
                item["evidence"] = json.loads(item["evidence_json"])
            except Exception:
                item["evidence"] = []
            cards.append(item)
        return cards

    # --- Approvals Queries ---
    def get_pending_approvals(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM approvals WHERE run_id = ? AND status = 'pending' ORDER BY created_at ASC;",
            (run_id,),
        )
        approvals = []
        for row in cur.fetchall():
            item = dict(row)
            try:
                item["options"] = json.loads(item["options_json"])
            except Exception:
                item["options"] = []
            approvals.append(item)
        return approvals

    def get_run_approvals(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM approvals WHERE run_id = ? ORDER BY created_at ASC;",
            (run_id,),
        )
        approvals = []
        for row in cur.fetchall():
            item = dict(row)
            try:
                item["options"] = json.loads(item["options_json"])
            except Exception:
                item["options"] = []
            approvals.append(item)
        return approvals

    # --- Telemetry, Permissions & Auditing ---
    def record_llm_call(
        self,
        run_id: str,
        provider: str,
        model: str,
        latency_ms: float,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        try:
            self.db.execute_write(
                """
                INSERT INTO llm_calls (run_id, provider, model, latency_ms, status, error, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (run_id, provider, model, latency_ms, status, error, now_iso()),
            )
        except Exception as e:
            logger.warning(f"Could not record LLM call telemetry: {e}")

    def record_permission_event(
        self,
        run_id: str,
        agent: str,
        tool: str,
        args_summary: str,
        tier: str,
        outcome: str,
        decided_by: str,
        reason: str,
    ) -> None:
        try:
            self.db.execute_write(
                """
                INSERT INTO permission_events (
                    run_id, timestamp, agent, tool, args_summary, tier, outcome, decided_by, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    run_id,
                    now_iso(),
                    agent,
                    tool,
                    args_summary,
                    tier,
                    outcome,
                    decided_by,
                    reason,
                ),
            )
        except Exception as e:
            logger.warning(f"Could not record permission audit row: {e}")

    def get_run_permission_events(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM permission_events WHERE run_id = ? ORDER BY id ASC;",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    # --- Decisions Board ---
    def record_decision(
        self,
        run_id: str,
        decision_id: str,
        topic: str,
        summary: str,
        agreed_by: List[str],
        thread_id: Optional[str] = None,
    ) -> str:
        self.ensure_run(run_id)
        self.db.execute_write(
            """
            INSERT INTO decisions (id, run_id, topic, summary, agreed_by_json, thread_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                summary = excluded.summary,
                agreed_by_json = excluded.agreed_by_json;
            """,
            (decision_id, run_id, topic, summary, json.dumps(agreed_by), thread_id, now_iso()),
        )
        return decision_id

    def get_run_decisions(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM decisions WHERE run_id = ? ORDER BY timestamp ASC;",
            (run_id,),
        )
        results = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["agreed_by"] = json.loads(d["agreed_by_json"])
            except Exception:
                d["agreed_by"] = []
            results.append(d)
        return results

    # --- Artifacts Tracking ---
    def record_artifact(
        self,
        artifact_id: str,
        run_id: str,
        name: str,
        path: str,
        content_type: str,
        size_bytes: int,
    ) -> str:
        self.ensure_run(run_id)
        self.db.execute_write(
            """
            INSERT INTO artifacts (id, run_id, name, path, content_type, size_bytes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                path = excluded.path,
                size_bytes = excluded.size_bytes;
            """,
            (artifact_id, run_id, name, path, content_type, size_bytes, now_iso()),
        )
        return artifact_id

    def get_run_artifacts(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at ASC;",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    # --- Steering Receipts ---
    def record_steer(
        self,
        steer_id: str,
        run_id: str,
        message_id: str,
        mode: str,
        prompt: str,
        status: str = "applied",
        plan_diff: Optional[Dict[str, Any]] = None,
        targets: Optional[List[str]] = None,
    ) -> str:
        self.ensure_run(run_id)
        diff_json = json.dumps(plan_diff) if plan_diff else None
        targets_json = json.dumps(targets or [])
        self.db.execute_write(
            """
            INSERT INTO steers (id, run_id, message_id, mode, status, prompt, plan_diff_json, targets_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                plan_diff_json = excluded.plan_diff_json;
            """,
            (steer_id, run_id, message_id, mode, status, prompt, diff_json, targets_json, now_iso()),
        )
        return steer_id

    def get_run_steers(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM steers WHERE run_id = ? ORDER BY timestamp ASC;",
            (run_id,),
        )
        results = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["plan_diff"] = json.loads(d["plan_diff_json"]) if d["plan_diff_json"] else None
            except Exception:
                d["plan_diff"] = None
            try:
                d["targets"] = json.loads(d["targets_json"]) if d["targets_json"] else []
            except Exception:
                d["targets"] = []
            results.append(d)
        return results

    # --- Delivery Decisions (Decision Layer / Jev) ---
    def record_delivery_decision(
        self,
        run_id: str,
        message_id: str,
        receiver: str,
        action: str,
        confidence: float,
        backend: str,
        latency_ms: float,
    ) -> int:
        self.ensure_run(run_id)
        cur = self.db.execute_write(
            """
            INSERT INTO delivery_decisions (run_id, message_id, receiver, action, confidence, backend, latency_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (run_id, message_id, receiver, action, confidence, backend, latency_ms, now_iso()),
        )
        return cur

    def get_run_delivery_decisions(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.db.execute_read(
            "SELECT * FROM delivery_decisions WHERE run_id = ? ORDER BY id ASC;",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_delivery_stats(self, run_id: str) -> Dict[str, Any]:
        cur = self.db.execute_read(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN action = 'deliver' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN action = 'drop' THEN 1 ELSE 0 END) as dropped,
                SUM(CASE WHEN action = 'summarize' THEN 1 ELSE 0 END) as summarized,
                AVG(confidence) as avg_confidence,
                AVG(latency_ms) as avg_latency_ms
            FROM delivery_decisions
            WHERE run_id = ?;
            """,
            (run_id,),
        )
        row = cur.fetchone()
        if not row or not row["total"]:
            return {"total": 0, "delivered": 0, "dropped": 0, "summarized": 0, "avg_confidence": 1.0, "avg_latency_ms": 0.0}
        return {
            "total": row["total"] or 0,
            "delivered": row["delivered"] or 0,
            "dropped": row["dropped"] or 0,
            "summarized": row["summarized"] or 0,
            "avg_confidence": round(row["avg_confidence"] or 1.0, 2),
            "avg_latency_ms": round(row["avg_latency_ms"] or 0.0, 2),
        }


_storage_instance: Optional[StorageService] = None


def get_storage(db: Optional[Database] = None) -> StorageService:
    global _storage_instance
    if _storage_instance is None or db is not None:
        _storage_instance = StorageService(db)
    return _storage_instance
