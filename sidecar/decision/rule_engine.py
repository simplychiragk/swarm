"""
Rule-Based Decision Layer Implementation.
Provides fallback/rule-based heuristics for routing, approval gating, and whiteboard filtering.

TODO(post-hack): Replace or augment with Jev decision model once API endpoints and credentials are confirmed.
"""

from typing import Optional, Dict, Any
from sidecar.models.contracts import Lane, FeedMessage, MessageType
from .interface import DecisionLayer


class RuleBasedDecisionLayer(DecisionLayer):
    """
    Heuristic rule-based implementation of the Swarm Decision Layer.
    """

    def route_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Lane:
        """
        Keyword-based task routing across lanes.
        """
        # TODO(post-hack): Replace keyword matching with Jev confidence-ranked routing
        text = task_description.lower()

        if any(k in text for k in ["schema", "database", "sql", "migration", "table", "postgres", "sqlite", "model"]):
            return Lane.DB
        if any(k in text for k in ["api", "server", "fastapi", "backend", "endpoint", "route", "controller"]):
            return Lane.BE
        if any(k in text for k in ["ui", "frontend", "component", "tailwind", "react", "html", "css", "button", "landing"]):
            return Lane.FE
        if any(k in text for k in ["test", "qa", "verify", "playwright", "cypress", "browser", "assert"]):
            return Lane.TEST
        if any(k in text for k in ["doc", "readme", "markdown", "research", "search", "fetch"]):
            return Lane.DOCS
        if any(k in text for k in ["deploy", "docker", "ci", "cd", "ops", "cloud", "release", "production"]):
            return Lane.OPS
        if any(k in text for k in ["figma", "design", "palette", "theme", "color", "typography", "icon"]):
            return Lane.DESIGN

        return Lane.NONE

    def needs_approval(self, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Checks if an action needs human sign-off before proceeding.
        """
        # TODO(post-hack): Integrate Jev probabilistic risk scoring
        action_lower = action.lower()
        high_risk_keywords = [
            "deploy",
            "production",
            "drop table",
            "delete",
            "destroy",
            "email customers",
            "publish",
            "payment",
            "secret",
        ]
        return any(k in action_lower for k in high_risk_keywords)

    def should_show_on_whiteboard(self, message: FeedMessage) -> bool:
        """
        Scribe filtering heuristic: determine which agent chatter generates honey on the whiteboard.
        """
        # Status milestones, completed tasks, and evidence are always worthy of honey summaries
        if message.type in (MessageType.STATUS, MessageType.TASK, MessageType.EVIDENCE):
            return True

        # Scribe messages themselves are usually summary declarations
        if message.sender.value == "scribe":
            return True

        # Queen strategic guidance is visible
        if message.sender.value == "queen" and len(message.content) > 30:
            return True

        # Skip granular worker back-and-forth chit-chat (nectar stays in feed)
        return False
