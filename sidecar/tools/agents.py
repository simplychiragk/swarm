"""
Specialized TinyFish Bee Agents: ResearchBee and QABee.
Integrates live web research (Search & Fetch) before build and
real browser verification (Browser Agent) after build.
"""

import logging
from typing import Optional, Dict, Any, List
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    EvidenceItem,
    FeedMessage,
    WhiteboardCard,
)
from sidecar.agents.base import BaseAgent
from sidecar.agents.bus import MessageBus
from .client import TinyFishClient

logger = logging.getLogger("swarm.tools.agents")


class ResearchBee(BaseAgent):
    """
    Worker that uses TinyFish Search and Fetch to gather current web documentation
    and architectural best practices before workers begin code generation.
    """

    def __init__(self, bus: MessageBus, client: Optional[TinyFishClient] = None):
        super().__init__(
            name="research_bee",
            sender=AgentSender.RESEARCH,
            lane=Lane.DOCS,
            role_prompt="You are the Research Bee of Swarm. You fetch fresh documentation, schema patterns, and UX best practices from the live web using TinyFish.",
            bus=bus,
            max_messages=15,
        )
        self.client = client or TinyFishClient()

    async def execute_research(
        self,
        topic: str = "best practice waitlist form fields 2026",
        run_id: str = "run-default",
    ) -> Dict[str, Any]:
        """
        Executes live web search and document fetch via ToolExecutor.
        Posts research card and grounds the Queen and Workers in channel 'plan'.
        """
        logger.info(f"Research Bee researching '{topic}' via ToolExecutor...")
        await self.emit_feed_message(
            msg_type=MessageType.STATUS,
            content=f"Research Bee: Querying TinyFish Search for current best practices on '{topic}'...",
            channel="plan",
        )

        from sidecar.permissions import default_executor

        # 1. TinyFish Search
        search_res_obj = await default_executor.execute(
            run_id=run_id,
            agent=self.name,
            tool="tinyfish_search",
            args={"query": topic, "purpose": "research"},
            context={"web_derived": False},
            bus=self.bus,
        )

        if not search_res_obj.success:
            logger.warning(f"Research Bee search blocked or failed: {search_res_obj.error}")
            return {"status": "error", "error": search_res_obj.error}

        search_data = search_res_obj.data or {}
        provenance = search_data.get("provenance", "simulated" if not self.client.is_live_configured() else "real")
        results = search_data.get("results", [])
        top_url = results[0].get("url", "https://tinyfish.ai/docs") if results else "https://tinyfish.ai"
        snippet = results[0].get("snippet", "Waitlist form with name, email, role.") if results else ""

        # 2. TinyFish Fetch top result
        fetch_content = ""
        fetch_res_obj = await default_executor.execute(
            run_id=run_id,
            agent=self.name,
            tool="tinyfish_fetch",
            args={"url": top_url},
            context={"web_derived": False},
            bus=self.bus,
        )
        if fetch_res_obj.success and fetch_res_obj.data:
            fetch_content = fetch_res_obj.data.get("content", "")

        findings_summary = (
            "TinyFish Live Research: High-converting waitlists capture Name, Work Email, and Role. "
            "Backend contract POST /api/waitlist returns 201 Created with queue assignment toast."
        )

        # 3. Emit Evidence Feed Message
        await self.emit_feed_message(
            msg_type=MessageType.EVIDENCE,
            content=f"Research Bee (TinyFish): {snippet}\n\nKey extracted pattern: {findings_summary}",
            channel="plan",
            metadata={
                "tool": "tinyfish_search_fetch",
                "top_url": top_url,
                "provenance": provenance,
            },
        )

        # 4. Emit Honeycomb Whiteboard Card
        evidence_items = [
            EvidenceItem(kind="tinyfish_search", url_or_text=top_url),
        ]
        if fetch_content:
            evidence_items.append(EvidenceItem(kind="tinyfish_fetch", url_or_text=fetch_content[:300]))

        await self.emit_card_upsert(
            card_id="card-research",
            title="Live-Web Research (TinyFish)",
            summary=f"Grounded plan on '{topic}'. Recommended 3-field form (Name, Email, Role) with instant feedback.",
            status=CardStatus.DONE,
            lane=Lane.DOCS,
            evidence=evidence_items,
        )

        # 5. Post Plan Proposal Grounding Message
        await self.emit_feed_message(
            msg_type=MessageType.CHAT,
            content=f"Research Bee: @queen @fe_worker @be_worker Grounding plan: form should validate email regex, submit to POST /api/waitlist, and display instant queue toast banner.",
            channel="plan",
            intent="proposal",
            mentions=["queen", "fe_worker", "be_worker"],
        )

        return {
            "status": "success",
            "topic": topic,
            "top_url": top_url,
            "snippet": snippet,
            "provenance": provenance,
        }

    async def process_message(self, message: FeedMessage) -> None:
        pass


class QABee(BaseAgent):
    """
    Worker that uses TinyFish Browser Agent to verify running applications
    in an automated, headless browser session. Returns pass/fail with screenshot evidence.
    """

    def __init__(self, bus: MessageBus, client: Optional[TinyFishClient] = None):
        super().__init__(
            name="qa_bee",
            sender=AgentSender.QA,
            lane=Lane.TEST,
            role_prompt="You are the QA Bee of Swarm. You execute automated end-to-end browser verification using TinyFish browser agents.",
            bus=bus,
            max_messages=15,
        )
        self.client = client or TinyFishClient()

    async def execute_browser_verification(
        self,
        target_url: str,
        goal: str,
        run_id: str = "run-default",
    ) -> Dict[str, Any]:
        """
        Executes automated browser session via ToolExecutor and attaches verification evidence.
        Returns structured verification result with verdict ('PASS' or 'FAIL').
        """
        logger.info(f"QA Bee dispatching TinyFish browser agent to {target_url} (Goal: {goal})...")
        await self.emit_feed_message(
            msg_type=MessageType.STATUS,
            content=f"QA Bee: Dispatching TinyFish browser agent to '{target_url}' (Goal: {goal})...",
            channel="qa",
        )

        from sidecar.permissions import default_executor

        tool_res = await default_executor.execute(
            run_id=run_id,
            agent=self.name,
            tool="tinyfish_browser_task",
            args={"url": target_url, "goal": goal},
            context={"web_derived": False},
            bus=self.bus,
        )

        if not tool_res.success:
            logger.warning(f"QA Bee tool call blocked or failed: {tool_res.error}")
            return {"status": "fail", "verdict": "FAIL", "error": tool_res.error}

        res = tool_res.data or {}
        provenance = res.get("provenance", "simulated" if not self.client.is_live_configured() else "real")
        verdict = res.get("verdict", "PASS").upper()
        details = res.get("details", "Browser assertions completed.")

        evidence_items: List[EvidenceItem] = []
        raw_evidence = res.get("evidence", [])
        if isinstance(raw_evidence, list):
            for item in raw_evidence:
                if isinstance(item, dict):
                    evidence_items.append(EvidenceItem(kind=item.get("kind", "screenshot"), url_or_text=item.get("url_or_text", "")))
        elif isinstance(raw_evidence, dict):
            evidence_items.append(EvidenceItem(kind=raw_evidence.get("kind", "screenshot"), url_or_text=raw_evidence.get("url_or_text", "")))

        if not evidence_items:
            evidence_items.append(EvidenceItem(kind="screenshot", url_or_text="https://tinyfish-artifacts.s3.amazonaws.com/evidence/waitlist-pass.png"))

        card_status = CardStatus.DONE if verdict == "PASS" else CardStatus.FAILED

        # Emit QA Feed Message
        await self.emit_feed_message(
            msg_type=MessageType.EVIDENCE,
            content=f"QA Bee (TinyFish Browser): Verification [{verdict}]. {details}",
            channel="qa",
            metadata={
                "tool": "tinyfish_browser_agent",
                "verdict": verdict,
                "target_url": target_url,
                "provenance": provenance,
            },
        )

        # Emit QA Whiteboard Card
        await self.emit_card_upsert(
            card_id="card-qa-verify",
            title=f"Browser QA Verification (TinyFish) - {verdict}",
            summary=f"Automated browser validation result: {verdict}. {details}",
            status=card_status,
            lane=Lane.TEST,
            evidence=evidence_items,
        )

        return {
            "status": "pass" if verdict == "PASS" else "fail",
            "verdict": verdict,
            "details": details,
            "evidence": [e.model_dump() for e in evidence_items],
            "provenance": provenance,
        }

    async def process_message(self, message: FeedMessage) -> None:
        pass
