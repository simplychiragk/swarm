"""
Base Agent class for Swarm.
Provides inbox processing, message generation helpers, bus publication, and message limit guards.
"""

import uuid
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
    WhiteboardCard,
    ApprovalRequest,
    EvidenceItem,
)
from .bus import MessageBus

logger = logging.getLogger("swarm.agents.base")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentMessageLimitError(Exception):
    """Raised when an agent exceeds its assigned message allocation."""
    pass


class BaseAgent(ABC):
    """Abstract base class for all Swarm agents."""

    def __init__(
        self,
        name: str,
        sender: AgentSender,
        lane: Lane,
        role_prompt: str,
        bus: MessageBus,
        max_messages: int = 25,
    ):
        self.name = name
        self.sender = sender
        self.lane = lane
        self.role_prompt = role_prompt
        self.bus = bus
        self.max_messages = max_messages
        self.message_count = 0
        self.inbox: asyncio.Queue[FeedMessage] = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def emit_feed_message(
        self,
        msg_type: MessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        lane: Optional[Lane] = None,
    ) -> FeedMessage:
        """Constructs, records, and publishes a FeedMessage across the message bus."""
        if self.message_count >= self.max_messages:
            err_msg = f"Agent '{self.name}' exceeded maximum message limit ({self.max_messages}). Halting."
            logger.error(err_msg)
            raise AgentMessageLimitError(err_msg)

        self.message_count += 1
        msg = FeedMessage(
            id=f"msg-{self.sender.value}-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso(),
            sender=self.sender,
            lane=lane or self.lane,
            type=msg_type,
            content=content,
            metadata=metadata or {},
        )
        await self.bus.publish_feed_message(msg)
        return msg

    async def emit_card_upsert(
        self,
        card_id: str,
        title: str,
        summary: str,
        status: CardStatus,
        lane: Optional[Lane] = None,
        evidence: Optional[List[EvidenceItem]] = None,
    ) -> WhiteboardCard:
        """Constructs and broadcasts a Honeycomb WhiteboardCard update."""
        card = WhiteboardCard(
            id=card_id,
            title=title,
            summary=summary,
            status=status,
            lane=lane or self.lane,
            evidence=evidence,
            updated_at=now_iso(),
        )
        await self.bus.publish_card_upsert(card)
        return card

    async def emit_approval_request(
        self,
        request_id: str,
        card_id: str,
        prompt: str,
        options: List[str],
        lane: Optional[Lane] = None,
        card: Optional[WhiteboardCard] = None,
    ) -> ApprovalRequest:
        """Constructs and broadcasts a user ApprovalRequest gate."""
        req = ApprovalRequest(
            id=request_id,
            card_id=card_id,
            prompt=prompt,
            options=options,
            lane=lane or self.lane,
            card=card,
            created_at=now_iso(),
        )
        await self.bus.publish_approval_request(req)
        return req

    async def receive(self, message: FeedMessage) -> None:
        """Pushes an incoming message into the agent's inbox queue."""
        await self.inbox.put(message)

    @abstractmethod
    async def process_message(self, message: FeedMessage) -> None:
        """Processes an incoming message from the inbox."""
        pass

    async def _loop(self) -> None:
        self._running = True
        logger.info(f"Agent '{self.name}' loop started.")
        try:
            while self._running:
                try:
                    message = await asyncio.wait_for(self.inbox.get(), timeout=0.5)
                    await self.process_message(message)
                    self.inbox.task_done()
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info(f"Agent '{self.name}' loop cancelled.")
        except Exception as e:
            logger.error(f"Error in agent '{self.name}' loop: {e}", exc_info=True)
        finally:
            self._running = False

    def start(self) -> None:
        if not self._running:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
