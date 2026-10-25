"""
Scribe Agent for Swarm.
Subscribes to the live agent feed (nectar), batches messages, filters with the DecisionLayer,
and synthesizes clean plain-language Honeycomb Whiteboard updates (honey).
"""

import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
)
from sidecar.llm import complete
from sidecar.decision import RuleBasedDecisionLayer
from .base import BaseAgent
from .bus import MessageBus

logger = logging.getLogger("swarm.agents.scribe")


class HoneyCardUpdate(BaseModel):
    title: str = Field(..., description="Short card title")
    summary: str = Field(..., description="Plain-language summary of completed or ongoing work")
    status: str = Field(default="in_progress", description="Card status: in_progress, done, planned")
    lane: str = Field(default="none", description="Domain lane")


class ScribeAgent(BaseAgent):
    """Scribe agent synthesizing live agent conversation into whiteboard cards."""

    def __init__(
        self,
        bus: MessageBus,
        decision_layer: Optional[RuleBasedDecisionLayer] = None,
        batch_interval: float = 2.5,
        max_messages: int = 200,
    ):
        super().__init__(
            name="scribe",
            sender=AgentSender.SCRIBE,
            lane=Lane.NONE,
            role_prompt="You are the Scribe of Swarm. You convert raw developer chatter into clean plain-language summary cards for stakeholders.",
            bus=bus,
            max_messages=max_messages,
        )
        self.decision_layer = decision_layer or RuleBasedDecisionLayer()
        self.batch_interval = batch_interval
        self._message_batch: List[FeedMessage] = []
        self._batch_lock = asyncio.Lock()
        self._scribe_loop_task: Optional[asyncio.Task] = None

    async def process_message(self, message: FeedMessage) -> None:
        """Queue message for periodic summarization."""
        if message.sender != AgentSender.SCRIBE:
            async with self._batch_lock:
                self._message_batch.append(message)

    async def _periodic_summarizer(self) -> None:
        """Flushes and summarizes accumulated nectar every batch_interval seconds."""
        logger.info("Scribe periodic summarizer started.")
        try:
            while self._running:
                await asyncio.sleep(self.batch_interval)
                async with self._batch_lock:
                    if not self._message_batch:
                        continue
                    current_batch = list(self._message_batch)
                    self._message_batch.clear()

                # Filter using decision layer heuristics
                worthy_messages = [m for m in current_batch if self.decision_layer.should_show_on_whiteboard(m)]
                if not worthy_messages:
                    continue

                batch_text = "\n".join(f"[{m.sender.value}|{m.lane.value}]: {m.content}" for m in worthy_messages)
                res = await complete(
                    messages=[
                        {"role": "system", "content": f"{self.role_prompt}\nSummarize these raw updates into ONE clean progress card."},
                        {"role": "user", "content": batch_text},
                    ],
                    tier="fast",
                    json_schema=HoneyCardUpdate,
                )
                card_data: HoneyCardUpdate = res.parsed  # type: ignore
                if card_data:
                    card_status = CardStatus.IN_PROGRESS
                    if card_data.status.lower() in ("done", "completed"):
                        card_status = CardStatus.DONE

                    resolved_lane = Lane.NONE
                    try:
                        resolved_lane = Lane(card_data.lane)
                    except ValueError:
                        pass

                    await self.emit_card_upsert(
                        card_id=f"card-scribe-{resolved_lane.value.lower()}",
                        title=card_data.title,
                        summary=card_data.summary,
                        status=card_status,
                        lane=resolved_lane,
                    )

                    await self.emit_feed_message(
                        msg_type=MessageType.STATUS,
                        content=f"Scribe posted whiteboard card: '{card_data.title}'",
                    )
        except asyncio.CancelledError:
            logger.info("Scribe periodic summarizer cancelled.")
        except Exception as e:
            logger.error(f"Error in Scribe periodic summarizer: {e}", exc_info=True)

    def start(self) -> None:
        super().start()
        self._scribe_loop_task = asyncio.create_task(self._periodic_summarizer())

    async def stop(self) -> None:
        if self._scribe_loop_task and not self._scribe_loop_task.done():
            self._scribe_loop_task.cancel()
            try:
                await self._scribe_loop_task
            except asyncio.CancelledError:
                pass
        await super().stop()
