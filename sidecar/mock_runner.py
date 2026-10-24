"""
Mock Event Generator for Swarm.
Emits a realistic fake run of the waitlist landing page scenario from Section 9 of SWARM_CONTEXT.md.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
    WhiteboardCard,
    ApprovalRequest,
    EvidenceItem,
    FeedMessageEnvelope,
    CardUpsertEnvelope,
    ApprovalRequestEnvelope,
)
from sidecar.broadcaster import broadcaster

logger = logging.getLogger("swarm.mock_runner")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_mock_scenario_steps() -> List[Dict[str, Any]]:
    """
    Returns the sequence of events mirroring Section 9:
    1. Queen asks about audience, style and form fields.
    2. Research bee pulls current form-handling docs via TinyFish.
    3. Frontend and backend bees build in parallel, messaging each other.
    4. Scribe posts each stage to the honeycomb whiteboard in real time.
    5. QA bee submits the form in a real browser via TinyFish and reports pass or fail with evidence.
    6. User approves or redirects from the whiteboard (approval request).
    """
    t = now_iso()

    return [
        # --- Stage 1: Queen discovery ---
        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-1",
                timestamp=t,
                sender=AgentSender.QUEEN,
                lane=Lane.NONE,
                type=MessageType.CHAT,
                content="Welcome to Swarm! I am the Queen bee. You requested: 'Build a landing page with a waitlist form.' What is your target audience, preferred visual theme, and which form fields should we capture?",
                metadata={"prompt": "Build a landing page with a waitlist form."},
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-discovery",
                title="Discovery & Goal Definition",
                summary="Queen interviewing user to lock specs: audience, dark/light theme, and required form fields.",
                status=CardStatus.IN_PROGRESS,
                lane=Lane.NONE,
                updated_at=t,
            )
        ).model_dump(),

        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-2",
                timestamp=t,
                sender=AgentSender.SYSTEM,
                lane=Lane.NONE,
                type=MessageType.CHAT,
                content="User: Audience is indie developers; dark honeycomb aesthetic; collect Name, Work Email, and Primary Role.",
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-discovery",
                title="Discovery & Goal Definition",
                summary="Specifications confirmed: developer audience, dark honeycomb design, Name/Email/Role fields.",
                status=CardStatus.DONE,
                lane=Lane.NONE,
                updated_at=t,
            )
        ).model_dump(),

        # --- Stage 2: Research Bee via TinyFish ---
        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-3",
                timestamp=t,
                sender=AgentSender.QUEEN,
                lane=Lane.DOCS,
                type=MessageType.TASK,
                content="Delegating: Research bee, query TinyFish for modern 2026 React form validation and server action patterns.",
            )
        ).model_dump(),

        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-4",
                timestamp=t,
                sender=AgentSender.RESEARCH,
                lane=Lane.DOCS,
                type=MessageType.EVIDENCE,
                content="TinyFish Search completed: Extracted current React + Zod schema validation rules and optimistic pending state patterns.",
                metadata={"tool": "tinyfish_search", "query": "modern react form validation server action patterns"},
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-research",
                title="Live-Web Research (TinyFish)",
                summary="Fetched fresh 2026 React form patterns & Zod validation schema via TinyFish Web Search.",
                status=CardStatus.DONE,
                lane=Lane.DOCS,
                evidence=[
                    EvidenceItem(kind="tinyfish_search", url_or_text="https://api.tinyfish.io/v1/search?q=react+form+best+practices"),
                    EvidenceItem(kind="doc_summary", url_or_text="Recommended Zod validator with email regex and anti-spam honey pot field."),
                ],
                updated_at=t,
            )
        ).model_dump(),

        # --- Stage 3: Worker parallel chatter (nectar) & Scribe summaries (honey) ---
        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-5",
                timestamp=t,
                sender=AgentSender.QUEEN,
                lane=Lane.BE,
                type=MessageType.TASK,
                content="Backend bee: Implement POST /api/waitlist endpoint. Frontend bee: Build dark hero section with honeycomb backdrop.",
            )
        ).model_dump(),

        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-6",
                timestamp=t,
                sender=AgentSender.WORKER,
                lane=Lane.BE,
                type=MessageType.CHAT,
                content="BE Worker: Setting up FastAPI route /api/waitlist with Pydantic request validator for email uniqueness.",
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-be",
                title="Backend API Route",
                summary="Building POST /api/waitlist with Pydantic validation and duplicate email check.",
                status=CardStatus.IN_PROGRESS,
                lane=Lane.BE,
                updated_at=t,
            )
        ).model_dump(),

        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-7",
                timestamp=t,
                sender=AgentSender.WORKER,
                lane=Lane.FE,
                type=MessageType.CHAT,
                content="FE Worker: Designing dark modern honeycomb hero card with Tailwind and Shadcn input fields.",
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-fe",
                title="Frontend Landing Page",
                summary="Designing responsive landing page: dark palette, animated hex grid, and waitlist form.",
                status=CardStatus.IN_PROGRESS,
                lane=Lane.FE,
                updated_at=t,
            )
        ).model_dump(),

        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-8",
                timestamp=t,
                sender=AgentSender.WORKER,
                lane=Lane.BE,
                type=MessageType.STATUS,
                content="BE Worker: /api/waitlist endpoint passes unit checks. Returns 201 Created with referral code.",
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-be",
                title="Backend API Route",
                summary="FastAPI endpoint ready and verified with mock database persistence.",
                status=CardStatus.DONE,
                lane=Lane.BE,
                updated_at=t,
            )
        ).model_dump(),

        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-9",
                timestamp=t,
                sender=AgentSender.WORKER,
                lane=Lane.FE,
                type=MessageType.STATUS,
                content="FE Worker: Integrated waitlist form with backend route. Added success modal and loading spinners.",
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-fe",
                title="Frontend Landing Page",
                summary="Landing UI complete and wired to backend submission API.",
                status=CardStatus.DONE,
                lane=Lane.FE,
                updated_at=t,
            )
        ).model_dump(),

        # --- Stage 4: Scribe bridge ---
        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-10",
                timestamp=t,
                sender=AgentSender.SCRIBE,
                lane=Lane.NONE,
                type=MessageType.STATUS,
                content="Scribe: Frontend and Backend integration complete. Routing to QA Bee for real browser testing via TinyFish.",
            )
        ).model_dump(),

        # --- Stage 5: QA Bee browser testing via TinyFish with evidence ---
        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-11",
                timestamp=t,
                sender=AgentSender.QA,
                lane=Lane.TEST,
                type=MessageType.STATUS,
                content="QA Bee: Dispatching TinyFish Browser Agent to navigate to http://localhost:5173, fill waitlist form, and verify confirmation message.",
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-qa",
                title="Browser QA Verification (TinyFish)",
                summary="TinyFish browser agent executing automated end-to-end form test in a real browser session.",
                status=CardStatus.IN_PROGRESS,
                lane=Lane.TEST,
                updated_at=t,
            )
        ).model_dump(),

        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-12",
                timestamp=t,
                sender=AgentSender.QA,
                lane=Lane.TEST,
                type=MessageType.EVIDENCE,
                content="QA Bee: Form submission verified! Received HTTP 201, toast 'You are #42 on the waitlist' rendered on screen. Attached screenshot evidence.",
                metadata={
                    "tool": "tinyfish_browser_agent",
                    "result": "PASS",
                    "duration_ms": 1420,
                    "screenshot_id": "tf-screenshot-waitlist-pass",
                },
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-qa",
                title="Browser QA Verification (TinyFish)",
                summary="End-to-end browser test PASSED: Form inputs submitted, HTTP 201 received, confirmation banner verified.",
                status=CardStatus.DONE,
                lane=Lane.TEST,
                evidence=[
                    EvidenceItem(kind="screenshot", url_or_text="https://tinyfish-demo.s3.amazonaws.com/evidence/waitlist_success.png"),
                    EvidenceItem(kind="browser_log", url_or_text="TinyFish runner: 3 assertions passed (Input populated, button clicked, toast shown)."),
                ],
                updated_at=t,
            )
        ).model_dump(),

        # --- Stage 6: Decision Layer gates production release -> Approval Request ---
        FeedMessageEnvelope(
            payload=FeedMessage(
                id="msg-13",
                timestamp=t,
                sender=AgentSender.QUEEN,
                lane=Lane.OPS,
                type=MessageType.TASK,
                content="Decision layer (Jev rules): Deploying to production edge is an external-facing action. User approval required.",
            )
        ).model_dump(),

        CardUpsertEnvelope(
            payload=WhiteboardCard(
                id="card-approval",
                title="Production Release Gate",
                summary="Build and TinyFish QA tests passed. Awaiting user authorization to publish the landing page live.",
                status=CardStatus.NEEDS_APPROVAL,
                lane=Lane.OPS,
                evidence=[
                    EvidenceItem(kind="qa_status", url_or_text="QA Passed 100%"),
                    EvidenceItem(kind="target_env", url_or_text="Cloudflare Pages / Vercel Edge"),
                ],
                updated_at=t,
            )
        ).model_dump(),

        ApprovalRequestEnvelope(
            payload=ApprovalRequest(
                id="approval-deploy-1",
                card_id="card-approval",
                prompt="The waitlist landing page is verified by TinyFish browser QA. Do you authorize publishing to the production domain?",
                options=["Approve & Deploy Live", "Request Copy Tweaks", "Reject Deployment"],
                lane=Lane.OPS,
                card=WhiteboardCard(
                    id="card-approval",
                    title="Production Release Gate",
                    summary="Build and TinyFish QA tests passed. Awaiting user authorization to publish the landing page live.",
                    status=CardStatus.NEEDS_APPROVAL,
                    lane=Lane.OPS,
                    updated_at=t,
                ),
                created_at=t,
            )
        ).model_dump(),
    ]


class MockRunner:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self.is_running: bool = False

    async def _run_stream(self, delay_seconds: float = 1.2):
        self.is_running = True
        try:
            logger.info("Starting mock scenario stream...")
            steps = get_mock_scenario_steps()
            for step in steps:
                # Update timestamp on the fly for freshness
                if "payload" in step and "timestamp" in step["payload"]:
                    step["payload"]["timestamp"] = now_iso()
                if "payload" in step and "updated_at" in step["payload"]:
                    step["payload"]["updated_at"] = now_iso()
                if "payload" in step and "created_at" in step["payload"]:
                    step["payload"]["created_at"] = now_iso()

                await broadcaster.broadcast(step)
                await asyncio.sleep(delay_seconds)
            logger.info("Mock scenario stream finished.")
        except asyncio.CancelledError:
            logger.info("Mock scenario stream cancelled.")
        except Exception as e:
            logger.error(f"Error during mock scenario: {e}", exc_info=True)
        finally:
            self.is_running = False

    def start(self, delay_seconds: float = 1.2) -> bool:
        if self.is_running and self._task and not self._task.done():
            logger.info("Mock runner already active.")
            return False
        self._task = asyncio.create_task(self._run_stream(delay_seconds=delay_seconds))
        return True

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self.is_running = False


mock_runner = MockRunner()
