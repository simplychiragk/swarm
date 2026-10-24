"""
Async In-Process Message Bus for Swarm Agents.
Receives FeedMessages from agents, routes to subscribers, and broadcasts to UI via WebSockets.
"""

import asyncio
import logging
from typing import List, Callable, Awaitable, Optional, Dict, Any
from sidecar.models.contracts import (
    FeedMessage,
    WhiteboardCard,
    ApprovalRequest,
    FeedMessageEnvelope,
    CardUpsertEnvelope,
    ApprovalRequestEnvelope,
)
from sidecar.broadcaster import broadcaster

logger = logging.getLogger("swarm.agents.bus")


class MessageBus:
    """Async message bus connecting agents and UI WebSocket streaming."""

    def __init__(self, run_id: str = "run-default"):
        self.run_id = run_id
        self._subscribers: List[Callable[[FeedMessage], Awaitable[None]]] = []
        self._history: List[FeedMessage] = []
        self._lock = asyncio.Lock()

    def subscribe(self, callback: Callable[[FeedMessage], Awaitable[None]]) -> None:
        """Register an async subscriber to the message feed."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[FeedMessage], Awaitable[None]]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def publish_feed_message(self, message: FeedMessage, provenance: str = "real") -> None:
        """Publishes a FeedMessage to subscribers and broadcasts to the UI WebSocket."""
        async with self._lock:
            self._history.append(message)
            if len(self._history) > 300:
                self._history = self._history[-300:]

        # Broadcast over WebSocket to Tauri / browser UI
        envelope = FeedMessageEnvelope(payload=message).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

        # Notify internal subscribers (workers, scribe)
        for sub in list(self._subscribers):
            try:
                await sub(message)
            except Exception as e:
                logger.error(f"Error notifying subscriber {sub}: {e}", exc_info=True)

    async def publish_card_upsert(self, card: WhiteboardCard, provenance: str = "real") -> None:
        """Broadcasts a WhiteboardCard upsert to the UI."""
        envelope = CardUpsertEnvelope(payload=card).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

    async def publish_approval_request(self, req: ApprovalRequest, provenance: str = "real") -> None:
        """Broadcasts an ApprovalRequest to the UI."""
        envelope = ApprovalRequestEnvelope(payload=req).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

    def get_history(self) -> List[FeedMessage]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()
