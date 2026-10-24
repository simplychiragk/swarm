"""
Worker Bee Agents for Swarm.
Owns execution in a specific lane (BE, FE). Calls LLM gateway for deliverables and coordinates with peer workers.
"""

import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
)
from sidecar.llm import complete
from .base import BaseAgent
from .bus import MessageBus

logger = logging.getLogger("swarm.agents.worker")


class DeliverableSchema(BaseModel):
    message: str = Field(..., description="Worker progress narrative")
    technical_spec: str = Field(..., description="API contract or component markup outline")
    status: str = Field(default="done", description="Lifecycle status")


class WorkerAgent(BaseAgent):
    """Lane worker agent (Frontend or Backend)."""

    def __init__(self, name: str, lane: Lane, bus: MessageBus):
        role = (
            "You are a specialized Backend Engineer worker bee. You construct FastAPI endpoints, validators, and database schemas."
            if lane == Lane.BE
            else "You are a specialized Frontend Engineer worker bee. You build React, Vite, and Tailwind components matching backend API shapes."
        )
        super().__init__(
            name=name,
            sender=AgentSender.WORKER,
            lane=lane,
            role_prompt=role,
            bus=bus,
            max_messages=25,
        )
        self.received_peer_contract: Optional[str] = None
        self.active_task_id: Optional[str] = None

    async def write_deliverable_artifact(self, filename: str, content: str, run_id: str = "run-default") -> None:
        """
        Persists generated code files to the run workspace via ToolExecutor.
        """
        from sidecar.permissions import default_executor
        clean_name = filename.replace("sidecar/", "src/").replace("app/", "src/")
        tool_res = await default_executor.execute(
            run_id=run_id,
            agent=self.name,
            tool="file_write",
            args={"path": clean_name, "content": content},
            context={"web_derived": False},
            bus=self.bus,
        )
        if not tool_res.success:
            logger.warning(f"Worker deliverable write blocked: {tool_res.error}")
        else:
            logger.info(f"Worker '{self.name}' persisted deliverable '{clean_name}' ({len(content)} bytes)")

    async def execute_task(self, task_id: str, title: str, description: str) -> None:
        """Executes a delegated task with LLM completion and peer coordination."""
        self.active_task_id = task_id
        logger.info(f"Worker '{self.name}' starting task '{title}' [{self.lane.value}]")

        # Mark card in progress
        await self.emit_card_upsert(
            card_id=task_id,
            title=title,
            summary=f"Worker actively executing: {description}",
            status=CardStatus.IN_PROGRESS,
        )

        # Call LLM to produce work
        prompt = f"Task: {title}\nDescription: {description}"
        if self.received_peer_contract:
            prompt += f"\nPeer contract provided: {self.received_peer_contract}"

        res = await complete(
            messages=[
                {"role": "system", "content": self.role_prompt},
                {"role": "user", "content": prompt},
            ],
            tier="fast",
            json_schema=DeliverableSchema,
        )
        deliverable: DeliverableSchema = res.parsed  # type: ignore

        # Publish chatter
        await self.emit_feed_message(
            msg_type=MessageType.CHAT,
            content=f"{self.name.upper()}: {deliverable.message if deliverable else res.text}",
            metadata={"spec": deliverable.technical_spec if deliverable else ""},
        )

        # If Backend worker, notify Frontend worker with the API contract shape
        if self.lane == Lane.BE:
            contract_snippet = "POST /api/waitlist -> Request: {name: str, email: str, role: str} -> Response: 201 Created {id, referral_code}"
            await self.emit_feed_message(
                msg_type=MessageType.CHAT,
                content=f"BE Worker -> FE Worker: Locked API endpoint contract: `{contract_snippet}`",
                metadata={"contract": contract_snippet},
                lane=Lane.FE,
            )
            await self.write_deliverable_artifact("sidecar/routes/waitlist.py", deliverable.technical_spec if deliverable else "")

        # If Frontend worker, record component output
        if self.lane == Lane.FE:
            await self.write_deliverable_artifact("app/src/components/WaitlistHero.tsx", deliverable.technical_spec if deliverable else "")

        # Mark card done
        await self.emit_card_upsert(
            card_id=task_id,
            title=title,
            summary=f"Completed by {self.name.upper()}: {description}",
            status=CardStatus.DONE,
        )

        await self.emit_feed_message(
            msg_type=MessageType.STATUS,
            content=f"{self.name.upper()}: Task '{title}' completed successfully.",
        )

    async def process_message(self, message: FeedMessage) -> None:
        """Handle peer messages and incoming task assignments."""
        # Check if receiving a peer contract from another worker
        if message.sender == AgentSender.WORKER and message.lane == self.lane and "contract" in (message.metadata or {}):
            self.received_peer_contract = str(message.metadata.get("contract"))
            logger.info(f"Worker '{self.name}' received peer contract: {self.received_peer_contract}")
            await self.emit_feed_message(
                msg_type=MessageType.CHAT,
                content=f"{self.name.upper()}: Received contract from peer. Incorporating into frontend implementation.",
            )
            return

        # Check for task assignments
        if message.type == MessageType.TASK and message.lane == self.lane:
            task_id = (message.metadata or {}).get("task_id", f"task-{self.lane.value.lower()}")
            await self.execute_task(
                task_id=task_id,
                title=f"{self.lane.value} Task",
                description=message.content,
            )
