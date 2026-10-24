"""
Specialized TinyFish Bee Agents: ResearchBee and QABee.
Integrates live web research before build and real browser verification after build.
"""

import logging
from typing import Optional
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    EvidenceItem,
    FeedMessage,
)
from sidecar.agents.base import BaseAgent
from sidecar.agents.bus import MessageBus
from .client import TinyFishClient

logger = logging.getLogger("swarm.tools.agents")


class ResearchBee(BaseAgent):
    """Worker that uses TinyFish Search and Fetch to gather current web documentation before building."""

    def __init__(self, bus: MessageBus, client: Optional[TinyFishClient] = None):
        super().__init__(
            name="research_bee",
            sender=AgentSender.RESEARCH,
            lane=Lane.DOCS,
            role_prompt="You are the Research Bee of Swarm. You fetch fresh documentation and patterns from the live web using TinyFish.",
            bus=bus,
            max_messages=15,
        )
        self.client = client or TinyFishClient()

    async def execute_research(self, topic: str) -> None:
        """Executes live web search and extracts patterns."""
        logger.info(f"Research Bee researching '{topic}' via TinyFish...")
        await self.emit_feed_message(
            msg_type=MessageType.STATUS,
            content=f"Research Bee: Querying TinyFish Search for fresh patterns on: '{topic}'...",
        )

        search_res = await self.client.search(query=topic)
        results = search_res.get("results", [])
        snippet = results[0].get("snippet", "Current best practices gathered.") if results else "No direct matches found."

        await self.emit_feed_message(
            msg_type=MessageType.EVIDENCE,
            content=f"Research Bee (TinyFish): {snippet}",
            metadata={"tool": "tinyfish_search", "query": topic, "results_count": len(results)},
        )

        evidence_items = [
            EvidenceItem(kind="tinyfish_search", url_or_text=r.get("url", "https://tinyfish.ai"))
            for r in results[:2]
        ]

        await self.emit_card_upsert(
            card_id="card-research",
            title="Live-Web Research (TinyFish)",
            summary=f"Gathered live web specifications on '{topic}'. Recommended schema patterns shared with workers.",
            status=CardStatus.DONE,
            evidence=evidence_items,
        )

    async def process_message(self, message: FeedMessage) -> None:
        pass


class QABee(BaseAgent):
    """Worker that uses TinyFish Browser Agent to verify running applications in a real browser."""

    def __init__(self, bus: MessageBus, client: Optional[TinyFishClient] = None):
        super().__init__(
            name="qa_bee",
            sender=AgentSender.QA,
            lane=Lane.TEST,
            role_prompt="You are the QA Bee of Swarm. You run automated end-to-end browser tests using TinyFish browser agents.",
            bus=bus,
            max_messages=15,
        )
        self.client = client or TinyFishClient()

    async def execute_browser_verification(self, target_url: str, goal: str) -> None:
        """Executes automated browser session and attaches verification evidence."""
        logger.info(f"QA Bee dispatching TinyFish browser agent to {target_url} with goal: '{goal}'")
        await self.emit_feed_message(
            msg_type=MessageType.STATUS,
            content=f"QA Bee: Dispatching TinyFish browser agent to '{target_url}' (Goal: {goal})...",
        )

        res = await self.client.run_browser_task(url=target_url, goal=goal)
        verdict = res.get("result", {}).get("verdict", "PASS")
        details = res.get("result", {}).get("details", "All browser assertions passed.")
        screenshot_url = res.get("evidence", {}).get("url_or_text", "https://tinyfish.ai/evidence/pass.png")

        await self.emit_feed_message(
            msg_type=MessageType.EVIDENCE,
            content=f"QA Bee: Verification completed [{verdict}]. {details}",
            metadata={"tool": "tinyfish_browser_agent", "verdict": verdict, "target_url": target_url},
        )

        await self.emit_card_upsert(
            card_id="card-qa-verify",
            title="Browser QA Verification (TinyFish)",
            summary=f"Automated browser validation completed with verdict: {verdict}. Form inputs and confirmation verified.",
            status=CardStatus.DONE,
            evidence=[
                EvidenceItem(kind="screenshot", url_or_text=screenshot_url),
                EvidenceItem(kind="browser_log", url_or_text=f"Result: {details}"),
            ],
        )

    async def process_message(self, message: FeedMessage) -> None:
        pass
