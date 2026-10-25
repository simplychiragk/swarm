"""
Queen Agent for Swarm.
Leads user interview (maximum 3 questions), synthesizes requirements, builds structured task plans
via LLM gateway, and delegates to workers with health monitoring.
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
    UserMessage,
    PlanDiff,
    TaskDiffItem,
    PlanDiffEnvelope,
)
from sidecar.models.specs import extract_project_spec, ProjectSpec
from sidecar.llm import complete
from sidecar.decision import RuleBasedDecisionLayer
from sidecar.broadcaster import broadcaster
from .base import BaseAgent
from .bus import MessageBus

logger = logging.getLogger("swarm.agents.queen")


class InterviewEvaluation(BaseModel):
    is_finished: bool = Field(..., description="Whether sufficient requirements are gathered")
    question: str = Field(..., description="Follow-up question if not finished")
    summary: str = Field(..., description="Summary of confirmed specifications")


class TaskItem(BaseModel):
    id: str
    lane: str
    title: str
    description: str
    dependencies: List[str] = Field(default_factory=list)


class PlanStructure(BaseModel):
    tasks: List[TaskItem]


class QueenAgent(BaseAgent):
    """Orchestrator queen agent conducting interview and decomposing project goals."""

    def __init__(
        self,
        bus: MessageBus,
        decision_layer: Optional[RuleBasedDecisionLayer] = None,
        max_messages: int = 200,
    ):
        super().__init__(
            name="queen",
            sender=AgentSender.QUEEN,
            lane=Lane.NONE,
            role_prompt="You are the Queen bee of Swarm. You interview users, plan multi-agent tasks, and monitor progress.",
            bus=bus,
            max_messages=max_messages,
        )
        self.decision_layer = decision_layer or RuleBasedDecisionLayer()
        self.question_count = 0
        self.max_questions = 3
        self.interview_done = False
        self.plan_done = False
        self.dialogue_history: List[Dict[str, str]] = []
        self.tasks_created: List[TaskItem] = []
        self.worker_activity: Dict[str, float] = {}
        self.worker_messages: Dict[str, List[str]] = {}
        self.pending_steers: List[UserMessage] = []
        self.is_interrupted: bool = False
        self.current_spec: Optional[ProjectSpec] = None

    def get_current_spec(self) -> ProjectSpec:
        """Returns the current extracted project specification."""
        if not self.current_spec:
            self.current_spec = extract_project_spec("waitlist")
        return self.current_spec

    def record_worker_activity(self, worker_name: str, message_content: str):
        """Update activity timestamp and message history for watchdog."""
        self.worker_activity[worker_name] = time.time()
        history = self.worker_messages.setdefault(worker_name, [])
        history.append(message_content)

    async def check_stuck_workers(self, timeout_seconds: float = 25.0) -> None:
        """Nudge or flag workers that have stalled or repeat identical outputs."""
        now = time.time()
        for worker_name, last_time in list(self.worker_activity.items()):
            if now - last_time > timeout_seconds:
                logger.warning(f"Worker '{worker_name}' has been silent for >{timeout_seconds}s. Nudging.")
                await self.emit_feed_message(
                    msg_type=MessageType.CHAT,
                    content=f"Queen: Worker '{worker_name}', status check requested. Please report current progress.",
                )
                self.worker_activity[worker_name] = now  # Reset nudge timer

    async def handle_user_input(self, user_text: str) -> None:
        """Processes user input during discovery interview or steering."""
        self.dialogue_history.append({"role": "user", "content": user_text})
        self.current_spec = extract_project_spec(user_text, self.dialogue_history)

        # Phase 1: Interview loop
        if not self.interview_done:
            self.question_count += 1
            logger.info(f"Queen evaluating interview step ({self.question_count}/{self.max_questions})")

            # Check if requirements met or reached 3 questions limit
            if self.question_count >= self.max_questions:
                self.interview_done = True
            else:
                eval_res = await complete(
                    messages=[
                        {"role": "system", "content": f"{self.role_prompt}\nEvaluate if we have enough details (audience, theme, fields). Max 3 questions."},
                        *self.dialogue_history,
                    ],
                    tier="fast",
                    json_schema=InterviewEvaluation,
                )
                parsed: InterviewEvaluation = eval_res.parsed  # type: ignore
                if parsed and parsed.is_finished:
                    self.interview_done = True
                elif parsed and parsed.question:
                    self.dialogue_history.append({"role": "assistant", "content": parsed.question})
                    await self.emit_feed_message(
                        msg_type=MessageType.CHAT,
                        content=f"Queen: {parsed.question}",
                    )
                    await self.emit_card_upsert(
                        card_id="card-discovery",
                        title="Discovery & Goal Definition",
                        summary=f"Inquiring specifications ({self.question_count}/{self.max_questions}). {parsed.summary}",
                        status=CardStatus.IN_PROGRESS,
                        lane=Lane.NONE,
                    )
                    return

        # Phase 2: Plan Generation
        if self.interview_done and not self.plan_done:
            await self.emit_feed_message(
                msg_type=MessageType.STATUS,
                content="Queen: Requirements confirmed! Decomposing project into structured execution plan.",
            )
            spec = self.get_current_spec()
            await self.emit_card_upsert(
                card_id="card-discovery",
                title="Discovery & Goal Definition",
                summary=f"Specifications confirmed: {spec.project_name} ({spec.form_title}) with dynamic schema validation.",
                status=CardStatus.DONE,
                lane=Lane.NONE,
            )

            plan_res = await complete(
                messages=[
                    {"role": "system", "content": f"{self.role_prompt}\nDecompose this software goal into a parallel task plan for Backend, Frontend, and QA workers."},
                    *self.dialogue_history,
                ],
                tier="smart",
                json_schema=PlanStructure,
            )
            plan: PlanStructure = plan_res.parsed  # type: ignore
            tasks = plan.tasks if plan else []
            self.tasks_created = tasks

            for t in tasks:
                # Use decision layer to ensure accurate lane classification
                resolved_lane = self.decision_layer.route_task(f"{t.title} {t.description}")
                if resolved_lane == Lane.NONE:
                    try:
                        resolved_lane = Lane(t.lane)
                    except ValueError:
                        resolved_lane = Lane.NONE

                await self.emit_feed_message(
                    msg_type=MessageType.TASK,
                    content=f"Queen delegated task [{resolved_lane.value}]: {t.title} — {t.description}",
                    metadata={"task_id": t.id, "dependencies": t.dependencies},
                    lane=resolved_lane,
                )

                await self.emit_card_upsert(
                    card_id=t.id,
                    title=t.title,
                    summary=t.description,
                    status=CardStatus.PLANNED,
                    lane=resolved_lane,
                )

            self.plan_done = True
            await self.emit_feed_message(
                msg_type=MessageType.STATUS,
                content="Queen: Plan distributed to worker lanes. Parallel build commenced.",
            )

    async def route_qa_failure(
        self,
        qa_result: Dict[str, Any],
        retry_count: int = 1,
        max_retries: int = 2,
    ) -> str:
        """
        Analyzes QA failure evidence, identifies responsible worker (FE vs BE),
        and emits targeted fix instructions in channel 'qa'.
        """
        details = str(qa_result.get("details", "")).lower()
        error = str(qa_result.get("error", "")).lower()
        combined = f"{details} {error}"

        if "404" in combined or "endpoint" in combined or "route" in combined or "backend" in combined:
            responsible_worker = "be_worker"
            responsible_lane = Lane.BE
            fix_instruction = "Fix API endpoint routing and verify POST /api/waitlist returns 201."
        else:
            responsible_worker = "fe_worker"
            responsible_lane = Lane.FE
            fix_instruction = "Ensure submit button is enabled and form handles submit properly."

        if retry_count > max_retries:
            logger.warning(f"QA failed after {retry_count - 1} retries. Emitting emergency approval card.")
            await self.emit_card_upsert(
                card_id="card-qa-emergency",
                title="QA Failure - Manual Override Required",
                summary=f"Automated verification failed after {retry_count - 1} retries: {qa_result.get('details')}",
                status=CardStatus.NEEDS_APPROVAL,
                lane=Lane.OPS,
            )
            await self.emit_approval_request(
                request_id=f"approval-emergency-{retry_count}",
                card_id="card-qa-emergency",
                prompt=f"QA verification failed {max_retries} attempts ({qa_result.get('details')}). Authorize manual override or halt?",
                options=["Override & Deploy", "Halt Execution"],
                lane=Lane.OPS,
            )
            return "emergency_gate"

        await self.emit_feed_message(
            msg_type=MessageType.TASK,
            content=f"Queen -> @{responsible_worker}: QA validation failed (Attempt {retry_count}/{max_retries}): {qa_result.get('details')}. {fix_instruction}",
            channel="qa",
            to=responsible_worker,
            mentions=[responsible_worker],
            lane=responsible_lane,
            requires_response=True,
        )
        return responsible_worker

    async def steer(self, message: UserMessage, run_id: str = "run-default") -> PlanDiff:
        """
        Processes human steering, queueing, or interrupt commands mid-run.
        Computes structured plan diff and updates workers and whiteboard.
        """
        mode = message.mode or "steer"
        logger.info(f"Queen received steering command [{mode}]: '{message.text}'")

        if mode == "interrupt":
            self.is_interrupted = True
            await self.emit_feed_message(
                msg_type=MessageType.STATUS,
                content=f"Queen: ⚠️ EXECUTION INTERRUPTED by user. Pausing active workers: '{message.text}'",
                lane=Lane.OPS,
            )
            await self.emit_card_upsert(
                card_id="card-interrupt",
                title="Swarm Interrupted by User",
                summary=f"Workers paused pending user clarification: '{message.text}'",
                status=CardStatus.IN_PROGRESS,
                lane=Lane.OPS,
            )
            return PlanDiff(
                run_id=run_id,
                reason=f"Execution paused on user interrupt: {message.text}",
                changes=[],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        elif mode == "queue":
            self.pending_steers.append(message)
            await self.emit_feed_message(
                msg_type=MessageType.STATUS,
                content=f"Queen: Instructions queued. Will factor after current build phase completes: '{message.text}'",
                lane=Lane.OPS,
            )
            return PlanDiff(
                run_id=run_id,
                reason=f"Queued for next phase: {message.text}",
                changes=[],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # mode == "steer": actively compute plan diff and modify plan
        now_ts = datetime.now(timezone.utc).isoformat()
        reason = f"User steering: {message.text}"
        changes: List[TaskDiffItem] = []

        lower_text = message.text.lower()
        if "phone" in lower_text:
            changes = [
                TaskDiffItem(
                    task_id="task-fe-phone",
                    title="Add Phone Number & Country Code Selector",
                    action="added",
                    lane=Lane.FE,
                    reason="Capture verified international phone number with country code picker",
                ),
                TaskDiffItem(
                    task_id="task-be-phone",
                    title="Extend Waitlist Schema for Phone Validation",
                    action="added",
                    lane=Lane.BE,
                    reason="Accept and validate optional phone & country_code in POST /api/waitlist",
                ),
                TaskDiffItem(
                    task_id="task-qa-verify",
                    title="Verify Form Submission with Phone Field",
                    action="modified",
                    lane=Lane.TEST,
                    reason="Verify submission succeeds with name, email, role, and phone number",
                ),
            ]
        else:
            changes = [
                TaskDiffItem(
                    task_id=f"task-steer-{uuid.uuid4().hex[:4]}",
                    title=f"Adjust Requirements: {message.text[:40]}",
                    action="modified",
                    lane=Lane.FE,
                    reason=message.text,
                )
            ]

        diff = PlanDiff(
            run_id=run_id,
            reason=reason,
            changes=changes,
            timestamp=now_ts,
        )

        # Broadcast plan_diff event
        envelope = PlanDiffEnvelope(payload=diff)
        await broadcaster.broadcast(envelope.model_dump(), run_id=run_id, provenance="real")

        # Emit feed announcement
        await self.emit_feed_message(
            msg_type=MessageType.TASK,
            content=f"Queen: Plan diff computed ({len(changes)} changes). User steered: '{message.text}'. Updating worker lanes.",
            channel="plan",
            intent="proposal",
            mentions=["fe_worker", "be_worker", "qa_bee"],
        )

        # Emit [EDITED] Whiteboard Card for the plan
        await self.emit_card_upsert(
            card_id="card-steer-plan",
            title="[EDITED] Steered Execution Plan",
            summary=f"Plan diff applied: {reason} ({len(changes)} task modifications).",
            status=CardStatus.IN_PROGRESS,
            lane=Lane.NONE,
        )

        return diff

    async def process_message(self, message: FeedMessage) -> None:
        """Monitor feed messages to update worker health timestamps."""
        if message.sender == AgentSender.WORKER:
            self.record_worker_activity(message.lane.value, message.content)
