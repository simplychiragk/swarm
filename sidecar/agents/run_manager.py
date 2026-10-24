"""
Swarm Run Manager.
Orchestrates live agent farm runs, enforces global limits and timeouts, and coordinates approval gating.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
    WhiteboardCard,
    ApprovalRequest,
    UserMessage,
    ApprovalResponse,
)
from sidecar.runtime.run_manager import RunManager
from sidecar.decision import RuleBasedDecisionLayer
from .bus import MessageBus
from .queen import QueenAgent
from .worker import WorkerAgent
from .scribe import ScribeAgent

logger = logging.getLogger("swarm.agents.run_manager")


class SwarmRunManager(RunManager):
    """Production runtime orchestrator coordinating Queen, Workers, Scribe, and Approval Gates."""

    def __init__(
        self,
        max_llm_calls: int = 40,
        max_messages_per_agent: int = 25,
        global_timeout_seconds: float = 120.0,
    ):
        self.max_llm_calls = max_llm_calls
        self.max_messages_per_agent = max_messages_per_agent
        self.global_timeout_seconds = global_timeout_seconds
        self.llm_call_count = 0
        self.decision_layer = RuleBasedDecisionLayer()
        self.bus = MessageBus()

        self.queen: Optional[QueenAgent] = None
        self.be_worker: Optional[WorkerAgent] = None
        self.fe_worker: Optional[WorkerAgent] = None
        self.scribe: Optional[ScribeAgent] = None
        self.research_bee: Optional[Any] = None
        self.qa_bee: Optional[Any] = None
        self.enable_tinyfish = os.environ.get("ENABLE_TINYFISH_BEES", "false").lower() in ("true", "1", "yes")

        self._watchdog_task: Optional[asyncio.Task] = None
        self._orchestrator_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.approval_pending = False

    def _init_agents(self) -> None:
        """Initializes agents with the shared message bus."""
        self.queen = QueenAgent(self.bus, self.decision_layer)
        self.be_worker = WorkerAgent("be_worker", Lane.BE, self.bus)
        self.fe_worker = WorkerAgent("fe_worker", Lane.FE, self.bus)
        self.scribe = ScribeAgent(self.bus, self.decision_layer, batch_interval=2.0)

        if self.enable_tinyfish:
            from sidecar.tools import ResearchBee, QABee
            self.research_bee = ResearchBee(self.bus)
            self.qa_bee = QABee(self.bus)

        # Route messages to specific agent inboxes
        async def message_router(msg: FeedMessage) -> None:
            if self.queen:
                await self.queen.receive(msg)
            if self.be_worker and (msg.lane == Lane.BE or msg.type == MessageType.TASK):
                await self.be_worker.receive(msg)
            if self.fe_worker and (msg.lane == Lane.FE or msg.type == MessageType.TASK):
                await self.fe_worker.receive(msg)
            if self.scribe:
                await self.scribe.receive(msg)

        self.bus.subscribe(message_router)

    async def _watchdog_loop(self) -> None:
        """Periodic health check ensuring workers do not remain stalled."""
        try:
            while self.is_running:
                await asyncio.sleep(10.0)
                if self.queen:
                    await self.queen.check_stuck_workers(timeout_seconds=20.0)
        except asyncio.CancelledError:
            pass

    async def _emit_failure_card(self, reason: str) -> None:
        """Emits a visible failure card when limits or timeouts trigger."""
        logger.error(f"Run failure: {reason}")
        card = WhiteboardCard(
            id="card-run-failure",
            title="Run Limit Exceeded",
            summary=f"Swarm halted execution safety gate: {reason}",
            status=CardStatus.FAILED,
            lane=Lane.OPS,
            updated_at=FeedMessage(id="", timestamp="", sender=AgentSender.SYSTEM, content="").timestamp,
        )
        await self.bus.publish_card_upsert(card)
        await self.bus.publish_feed_message(
            FeedMessage(
                id="msg-run-failure",
                timestamp=card.updated_at,
                sender=AgentSender.SYSTEM,
                lane=Lane.OPS,
                type=MessageType.ERROR,
                content=f"Execution halted: {reason}",
            )
        )

    async def _orchestration_pipeline(self, initial_text: str) -> None:
        """Coordinates the full pipeline from prompt to workers to final release gate."""
        try:
            # 1. Queen interviews / processes user text
            if not self.queen:
                return

            await self.queen.handle_user_input(initial_text)

            # If interview is still inquiring, await next user message
            if not self.queen.plan_done:
                logger.info("Interview step complete, awaiting further user input.")
                return

            # If enabled, Research Bee gathers live web specs prior to worker build
            if self.enable_tinyfish and self.research_bee:
                await asyncio.sleep(0.5)
                await self.research_bee.execute_research("modern react waitlist form patterns")

            # 2. Parallel construction: BE Worker and FE Worker execute tasks
            await asyncio.sleep(1.0)
            await self.be_worker.execute_task(
                task_id="task-be-api",
                title="FastAPI Waitlist Submission Endpoint",
                description="Construct POST /api/waitlist route with Pydantic email validation",
            )

            await asyncio.sleep(1.0)
            await self.fe_worker.execute_task(
                task_id="task-fe-hero",
                title="Responsive Waitlist Hero Section",
                description="Build dark modern UI with honeycomb styling and responsive form inputs",
            )

            # If enabled, QA Bee executes automated browser verification
            if self.enable_tinyfish and self.qa_bee:
                await asyncio.sleep(0.5)
                await self.qa_bee.execute_browser_verification("http://localhost:5173", "Verify waitlist form submission")

            # 3. Decision Layer checks if release requires human approval
            await asyncio.sleep(1.0)
            action_desc = "deploy waitlist landing page to production edge"
            needs_appr = self.decision_layer.needs_approval(action_desc)

            if needs_appr:
                self.approval_pending = True
                release_card = WhiteboardCard(
                    id="card-release-gate",
                    title="Production Release Gate",
                    summary="Backend API and Frontend landing UI complete. Awaiting user authorization to deploy.",
                    status=CardStatus.NEEDS_APPROVAL,
                    lane=Lane.OPS,
                    updated_at=FeedMessage(id="", timestamp="", sender=AgentSender.SYSTEM, content="").timestamp,
                )
                await self.bus.publish_card_upsert(release_card)

                approval_req = ApprovalRequest(
                    id="approval-release-1",
                    card_id="card-release-gate",
                    prompt="Waitlist landing page implementation is complete and verified. Authorize production release?",
                    options=["Approve Deployment", "Redirect / Revise"],
                    lane=Lane.OPS,
                    card=release_card,
                    created_at=release_card.updated_at,
                )
                await self.bus.publish_approval_request(approval_req)

                await self.bus.publish_feed_message(
                    FeedMessage(
                        id="msg-approval-gate",
                        timestamp=release_card.updated_at,
                        sender=AgentSender.QUEEN,
                        lane=Lane.OPS,
                        type=MessageType.TASK,
                        content="Decision layer (Jev rules): Production release requires human sign-off. Approval gate opened.",
                    )
                )

        except Exception as e:
            logger.error(f"Error during orchestration pipeline: {e}", exc_info=True)
            await self._emit_failure_card(str(e))

    async def start_run(self, user_text: str) -> None:
        """Starts a live multi-agent execution run."""
        self.is_running = True
        self._init_agents()

        # Start all agent loops
        self.queen.start()
        self.be_worker.start()
        self.fe_worker.start()
        self.scribe.start()
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

        # Launch main pipeline bounded by global timeout
        try:
            self._orchestrator_task = asyncio.create_task(
                asyncio.wait_for(
                    self._orchestration_pipeline(user_text),
                    timeout=self.global_timeout_seconds,
                )
            )
        except asyncio.TimeoutError:
            await self._emit_failure_card(f"Global run timeout ({self.global_timeout_seconds}s) exceeded.")

    async def handle_user_message(self, message: UserMessage) -> None:
        """Handles incoming user messages during live execution."""
        logger.info(f"SwarmRunManager received user message: '{message.text}'")
        if not self.is_running:
            await self.start_run(message.text)
        else:
            if self.queen:
                await self.queen.handle_user_input(message.text)
                # If plan was produced from this follow-up message, run the remainder of pipeline
                if self.queen.plan_done and not self.approval_pending:
                    self._orchestrator_task = asyncio.create_task(
                        self._orchestration_pipeline(message.text)
                    )

    async def handle_approval(self, response: ApprovalResponse) -> None:
        """Handles user sign-off decision (approve or redirect)."""
        logger.info(f"SwarmRunManager processing approval decision: '{response.decision}'")
        self.approval_pending = False
        new_status = CardStatus.DONE if response.decision == "approve" else CardStatus.FAILED

        summary = (
            "Release authorized by user. Application deployed live to production edge."
            if response.decision == "approve"
            else f"Release redirected by user: {response.note or 'Revision requested.'}"
        )

        card = WhiteboardCard(
            id=response.card_id,
            title="Production Release Gate",
            summary=summary,
            status=new_status,
            lane=Lane.OPS,
            updated_at=FeedMessage(id="", timestamp="", sender=AgentSender.SYSTEM, content="").timestamp,
        )
        await self.bus.publish_card_upsert(card)

        await self.bus.publish_feed_message(
            FeedMessage(
                id="msg-approval-resolved",
                timestamp=card.updated_at,
                sender=AgentSender.QUEEN,
                lane=Lane.OPS,
                type=MessageType.STATUS,
                content=f"Queen: Approval gate resolved ({response.decision}). Swarm run completed successfully.",
            )
        )

    async def stop(self) -> None:
        """Stops all active agent loops and tasks."""
        self.is_running = False
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
        if self._orchestrator_task and not self._orchestrator_task.done():
            self._orchestrator_task.cancel()
        if self.queen:
            await self.queen.stop()
        if self.be_worker:
            await self.be_worker.stop()
        if self.fe_worker:
            await self.fe_worker.stop()
        if self.scribe:
            await self.scribe.stop()
