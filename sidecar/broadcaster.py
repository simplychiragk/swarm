"""
WebSocket Connection Manager and Broadcaster for Swarm.
Broadcasts EventEnvelope payloads to all connected Tauri / React frontend clients.
"""

import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("swarm.broadcaster")


class Broadcaster:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.history: List[Dict[str, Any]] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Active connections: {len(self.active_connections)}")

        # Send existing history to the newly connected client so it catches up immediately
        for event in self.history:
            try:
                await websocket.send_text(json.dumps(event))
            except Exception as e:
                logger.warning(f"Failed to replay event to new client: {e}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, event_data: Dict[str, Any]):
        """
        Record and broadcast event envelope to all active connections.
        """
        self.history.append(event_data)
        # Cap in-memory history to prevent unbounded growth during hackathon
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

    def clear_history(self):
        self.history.clear()


broadcaster = Broadcaster()
