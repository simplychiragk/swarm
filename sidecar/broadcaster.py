"""
WebSocket Connection Manager and Broadcaster for Swarm.
Broadcasts EventEnvelope payloads to all connected Tauri / React frontend clients.
Backed by SQLite persistence for catch-up and replay.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger("swarm.broadcaster")


class Broadcaster:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.history: List[Dict[str, Any]] = []

    async def connect(
        self,
        websocket: WebSocket,
        run_id: str = "run-default",
        after_seq: Optional[int] = None,
    ):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Active connections: {len(self.active_connections)} (run_id={run_id}, after_seq={after_seq})")

        # Catch-up logic via SQLite storage
        try:
            from sidecar.storage import get_storage
            storage = get_storage()

            if after_seq is not None:
                # Client provided after_seq: stream delta events
                events = storage.get_run_events(run_id, after_seq=after_seq)
                for ev in events:
                    envelope = {
                        "event": ev["event_type"],
                        "payload": ev["payload"],
                        "seq": ev["seq"],
                        "run_id": ev["run_id"],
                        "provenance": ev.get("provenance", "real"),
                    }
                    await websocket.send_text(json.dumps(envelope))
            else:
                # Initial connect: send latest cards projection first for fast whiteboard render
                cards = storage.get_run_cards(run_id)
                for card in cards:
                    card_env = {
                        "event": "card_upsert",
                        "payload": card,
                        "run_id": run_id,
                        "provenance": "real",
                    }
                    await websocket.send_text(json.dumps(card_env))

                # Send any active pending approvals
                pending = storage.get_pending_approvals(run_id)
                for appr in pending:
                    appr_env = {
                        "event": "approval_request",
                        "payload": appr,
                        "run_id": run_id,
                        "provenance": "real",
                    }
                    await websocket.send_text(json.dumps(appr_env))

                # Stream chronological events for feed chat catch-up
                events = storage.get_run_events(run_id, after_seq=0)
                if events:
                    for ev in events:
                        envelope = {
                            "event": ev["event_type"],
                            "payload": ev["payload"],
                            "seq": ev["seq"],
                            "run_id": ev["run_id"],
                            "provenance": ev.get("provenance", "real"),
                        }
                        await websocket.send_text(json.dumps(envelope))
                elif self.history:
                    # Fallback to in-memory history if DB has no events for this run
                    for event in self.history:
                        await websocket.send_text(json.dumps(event))

        except (WebSocketDisconnect, RuntimeError):
            # Client disconnected during initial catch-up streaming (e.g. browser refresh / Vite reload)
            self.disconnect(websocket)
            return
        except Exception as e:
            logger.warning(f"Error catching up client from storage: {e}")
            # Safe fallback to in-memory history
            for event in self.history:
                try:
                    await websocket.send_text(json.dumps(event))
                except Exception:
                    pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(
        self,
        event_data: Dict[str, Any],
        run_id: str = "run-default",
        provenance: str = "real",
    ):
        """
        Record to SQLite storage and broadcast event envelope to all active connections.
        """
        payload = event_data.get("payload", {})
        actual_run_id = run_id
        if isinstance(payload, dict) and payload.get("run_id"):
            actual_run_id = payload.get("run_id")
        elif event_data.get("run_id"):
            actual_run_id = event_data.get("run_id")

        actual_provenance = event_data.get("provenance") or provenance

        # Write to SQLite
        try:
            from sidecar.storage import get_storage
            event_type = event_data.get("event", "unknown")
            seq = get_storage().record_event(
                run_id=actual_run_id,
                event_type=event_type,
                payload=payload if isinstance(payload, dict) else {},
                provenance=actual_provenance,
            )
            if seq > 0:
                event_data["seq"] = seq
                event_data["run_id"] = actual_run_id
                event_data["provenance"] = actual_provenance
        except Exception as e:
            logger.warning(f"Could not persist event to SQLite: {e}")

        self.history.append(event_data)
        if len(self.history) > 200:
            self.history = self.history[-200:]

        payload_json = json.dumps(event_data)
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(payload_json)
            except Exception as exc:
                logger.warning(f"Error sending message to client: {exc}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_direct(self, event_data: Dict[str, Any]):
        """
        Broadcast directly without writing a new event to the DB (e.g. for replaying historical events).
        """
        payload_json = json.dumps(event_data)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload_json)
            except Exception as exc:
                logger.warning(f"Error sending replay message to client: {exc}")
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    def clear_history(self):
        self.history.clear()


broadcaster = Broadcaster()
