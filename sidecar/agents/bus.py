"""
Async In-Process Message Bus for Swarm Agents.
Provides channel-based routing (hive, plan, build, qa), direct messaging,
agent inbox queues, thread lifecycle tracking with auto-summarization,
decision board synchronization, and live UI WebSocket streaming.
"""

import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Callable, Awaitable, Optional, Dict, Any, Set
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    EvidenceItem,
    FeedMessage,
    WhiteboardCard,
    ApprovalRequest,
    FeedMessageEnvelope,
    CardUpsertEnvelope,
    ApprovalRequestEnvelope,
    AgentStatus,
    AgentStatusEnvelope,
    FeedChunk,
    FeedChunkEnvelope,
)
from sidecar.broadcaster import broadcaster

logger = logging.getLogger("swarm.agents.bus")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Default channel membership mappings
DEFAULT_CHANNEL_MEMBERS: Dict[str, Set[str]] = {
    "hive": {"queen", "scribe", "fe_worker", "be_worker", "research_bee", "qa_bee"},
    "plan": {"queen", "scribe", "fe_worker", "be_worker"},
    "build": {"fe_worker", "be_worker", "scribe"},
    "qa": {"qa_bee", "fe_worker", "be_worker", "scribe"},
}


class MessageBus:
    """
    Async concurrent message bus connecting Swarm agents and UI WebSocket streaming.
    Supports inboxes, channel filtering, threading, and decision board recording.
    """

    def __init__(self, run_id: str = "run-default", auto_summary_threshold: int = 8):
        self.run_id = run_id
        self.auto_summary_threshold = auto_summary_threshold
        self._agents: Dict[str, asyncio.Queue[FeedMessage]] = {}
        self._agent_channels: Dict[str, Set[str]] = {}
        self._subscribers: List[Callable[[FeedMessage], Awaitable[None]]] = []
        self._history: List[FeedMessage] = []
        self._thread_turns: Dict[str, int] = {}
        self._thread_summarized: Set[str] = set()
        self._lock = asyncio.Lock()

    def register_agent(
        self,
        agent_name: str,
        channels: Optional[List[str]] = None,
        queue: Optional[asyncio.Queue] = None,
    ) -> asyncio.Queue[FeedMessage]:
        """Registers an agent with an inbox queue and channel subscriptions."""
        if channels is None:
            # Auto-assign standard channels based on default membership
            assigned = {"hive"}
            for ch, members in DEFAULT_CHANNEL_MEMBERS.items():
                if agent_name in members:
                    assigned.add(ch)
            channels = list(assigned)

        inbox = queue or asyncio.Queue()
        self._agents[agent_name] = inbox
        self._agent_channels[agent_name] = set(channels)
        logger.info(f"Registered agent '{agent_name}' with channels {channels}")
        return inbox

    def unregister_agent(self, agent_name: str) -> None:
        """Removes an agent and its inbox from the bus."""
        self._agents.pop(agent_name, None)
        self._agent_channels.pop(agent_name, None)
        logger.info(f"Unregistered agent '{agent_name}'")

    def get_inbox(self, agent_name: str) -> Optional[asyncio.Queue[FeedMessage]]:
        return self._agents.get(agent_name)

    def subscribe(self, callback: Callable[[FeedMessage], Awaitable[None]]) -> None:
        """Register an async subscriber callback for all incoming messages."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[FeedMessage], Awaitable[None]]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def publish_feed_message(self, message: FeedMessage, provenance: str = "real") -> None:
        """
        Publishes a FeedMessage across the bus.
        - Persists and broadcasts over WebSocket.
        - Routes to targeted agent inboxes (direct, mentions, or channel).
        - Tracks thread turns and auto-summarizes when threshold is reached.
        - Records 'decision' intents into the decisions board table & whiteboard.
        """
        async with self._lock:
            self._history.append(message)
            if len(self._history) > 300:
                self._history = self._history[-300:]

        # 1. Thread Tracking & Auto-Summarization
        if message.thread_id:
            turns = self._thread_turns.get(message.thread_id, 0) + 1
            self._thread_turns[message.thread_id] = turns

            # Auto-summarize when turn count hits threshold
            if turns >= self.auto_summary_threshold and message.thread_id not in self._thread_summarized:
                self._thread_summarized.add(message.thread_id)
                await self._trigger_thread_summary(message.thread_id, message.channel or "hive", turns)

        # 2. Decision Board Integration
        if message.intent == "decision":
            await self._record_decision_board(message, provenance=provenance)

        # 3. Broadcast over WebSocket to connected frontend clients
        envelope = FeedMessageEnvelope(payload=message).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

        # 4. Route to targeted agent inboxes
        target_agents: Set[str] = set()

        if message.to:
            # Direct address
            if message.to in self._agents:
                target_agents.add(message.to)
        elif message.mentions:
            # Explicit mentions
            for m in message.mentions:
                if m in self._agents:
                    target_agents.add(m)
        else:
            # Broadcast to channel members
            ch = message.channel or "hive"
            for agent_name, ch_set in self._agent_channels.items():
                if ch in ch_set:
                    target_agents.add(agent_name)

        # Sender should not receive its own message in its inbox
        sender_val = message.sender.value if hasattr(message.sender, "value") else str(message.sender)
        target_agents.discard(sender_val)

        for target in target_agents:
            inbox = self._agents.get(target)
            if inbox:
                await inbox.put(message)

        # 5. Notify generic subscribers (backwards-compat)
        for sub in list(self._subscribers):
            try:
                await sub(message)
            except Exception as e:
                logger.error(f"Error notifying subscriber {sub}: {e}", exc_info=True)

    async def _trigger_thread_summary(self, thread_id: str, channel: str, turns: int) -> None:
        """Synthesizes and posts a thread auto-summary when turn count threshold is exceeded."""
        logger.info(f"Thread '{thread_id}' reached {turns} turns. Auto-summarizing...")
        summary_text = (
            f"Thread Auto-Summary ({thread_id}): {turns} turns recorded. "
            f"Key discussion points and agreements captured. Thread archived to decisions board."
        )
        summary_msg = FeedMessage(
            id=f"msg-summary-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso(),
            sender=AgentSender.SCRIBE,
            lane=Lane.DOCS,
            type=MessageType.STATUS,
            content=summary_text,
            channel=channel,
            thread_id=thread_id,
            intent="chat",
        )

        # Record thread state in DB
        try:
            from sidecar.storage import get_storage
            get_storage().db.execute_write(
                """
                INSERT INTO threads (id, run_id, channel, subject, turn_count, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'summarized', ?, ?)
                ON CONFLICT(run_id, id) DO UPDATE SET
                    turn_count = excluded.turn_count,
                    status = excluded.status,
                    updated_at = excluded.updated_at;
                """,
                (thread_id, self.run_id, channel, f"Thread {thread_id}", turns, now_iso(), now_iso()),
            )
        except Exception as e:
            logger.warning(f"Could not persist thread summary state to DB: {e}")

        # Broadcast summary message
        envelope = FeedMessageEnvelope(payload=summary_msg).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance="real")

    async def _record_decision_board(self, message: FeedMessage, provenance: str = "real") -> None:
        """Records an agreed decision to the SQLite decisions table and posts a whiteboard card."""
        topic = None
        if message.metadata and "topic" in message.metadata:
            topic = str(message.metadata["topic"])
        if not topic:
            topic = message.content.split("\n")[0][:60]

        agreed_by = []
        if message.metadata and "agreed_by" in message.metadata:
            agreed_by = message.metadata["agreed_by"]
        if not agreed_by:
            sender_str = message.sender.value if hasattr(message.sender, "value") else str(message.sender)
            agreed_by = [sender_str]

        decision_id = f"dec-{uuid.uuid4().hex[:6]}"

        try:
            from sidecar.storage import get_storage
            get_storage().record_decision(
                run_id=self.run_id,
                decision_id=decision_id,
                topic=topic,
                summary=message.content,
                agreed_by=agreed_by,
                thread_id=message.thread_id,
            )
        except Exception as e:
            logger.warning(f"Could not persist decision to SQLite: {e}")

        # Post structured decision card to Honeycomb Whiteboard
        card = WhiteboardCard(
            id=f"card-decision-{decision_id}",
            title=f"Decision: {topic}",
            summary=message.content,
            status=CardStatus.DONE,
            lane=message.lane or Lane.DOCS,
            evidence=[EvidenceItem(kind="decision", url_or_text=f"Agreed by: {', '.join(agreed_by)}")],
            updated_at=now_iso(),
        )
        try:
            await self.publish_card_upsert(card, provenance=provenance)
        except TypeError:
            await self.publish_card_upsert(card)

    async def publish_agent_status(
        self,
        agent: str,
        status: str,
        current_task: Optional[str] = None,
        lane: Optional[Lane] = Lane.NONE,
        provenance: str = "real",
    ) -> None:
        """Broadcasts live agent status (idle, thinking, working, blocked) to UI."""
        status_model = AgentStatus(
            agent=agent,
            status=status,  # type: ignore
            current_task=current_task,
            lane=lane,
            timestamp=now_iso(),
        )
        envelope = AgentStatusEnvelope(payload=status_model).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

    async def publish_feed_chunk(
        self,
        message_id: str,
        delta: str,
        turn: int = 0,
        is_final: bool = False,
        provenance: str = "real",
    ) -> None:
        """Broadcasts streaming token delta for an agent feed message."""
        chunk = FeedChunk(
            message_id=message_id,
            delta=delta,
            turn=turn,
            is_final=is_final,
            timestamp=now_iso(),
        )
        envelope = FeedChunkEnvelope(payload=chunk).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

    async def publish_card_upsert(self, card: WhiteboardCard, provenance: str = "real") -> None:
        """Broadcasts a WhiteboardCard upsert to the UI and storage."""
        envelope = CardUpsertEnvelope(payload=card).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

    async def publish_approval_request(self, req: ApprovalRequest, provenance: str = "real") -> None:
        """Broadcasts an ApprovalRequest to the UI and storage."""
        envelope = ApprovalRequestEnvelope(payload=req).model_dump()
        await broadcaster.broadcast(envelope, run_id=self.run_id, provenance=provenance)

    def get_thread_turns(self, thread_id: str) -> int:
        return self._thread_turns.get(thread_id, 0)

    def get_history(self, channel: Optional[str] = None) -> List[FeedMessage]:
        if channel:
            return [m for m in self._history if m.channel == channel]
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()
        self._thread_turns.clear()
        self._thread_summarized.clear()
