"""
Rule-Based Decision Layer Implementation.
Provides fallback/rule-based heuristics for routing, approval gating, and whiteboard filtering.

TODO(post-hack): Replace or augment with Jev decision model once API endpoints and credentials are confirmed.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, Tuple, Union
from sidecar.models.contracts import Lane, FeedMessage, MessageType
from .interface import DecisionLayer

logger = logging.getLogger("swarm.decision.rule_engine")


class RuleBasedDecisionLayer(DecisionLayer):
    """
    Heuristic rule-based implementation of the Swarm Decision Layer.
    Includes optional Jev model integration with 500ms timeout fallback.
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

    def should_show_on_whiteboard(self, message: FeedMessage, return_confidence: bool = False) -> Any:
        """
        Scribe filtering heuristic: determine which agent chatter generates honey on the whiteboard.
        High confidence (>= 0.8) produces a card; low confidence stays in nectar feed.
        """
        confidence = 0.5
        worthy = False

        if message.type in (MessageType.STATUS, MessageType.TASK, MessageType.EVIDENCE):
            worthy = True
            confidence = 0.95
        elif message.sender.value == "scribe":
            worthy = True
            confidence = 0.90
        elif message.sender.value == "queen" and len(message.content) > 30:
            worthy = True
            confidence = 0.85
        elif getattr(message, "intent", None) == "decision":
            worthy = True
            confidence = 0.95

        if return_confidence:
            return worthy, confidence
        return worthy

    def decide_delivery(
        self,
        message: FeedMessage,
        receiver: str,
        run_id: str = "run-default",
    ) -> Dict[str, Any]:
        """
        Filters message delivery across agent inboxes.
        Evaluates deterministic rules, or calls Jev if configured.
        Logs every decision into SQLite table delivery_decisions.
        Returns: {action: 'deliver' | 'drop' | 'summarize', confidence: float, backend: str, latency_ms: float}
        """
        start = time.perf_counter()
        action = "deliver"
        confidence = 0.95
        backend = "rules"

        # Check for optional Jev model configuration
        jev_api_key = os.environ.get("JEV_API_KEY")
        if jev_api_key:
            try:
                action, confidence = self._query_jev(message, receiver)
                backend = "jev"
            except Exception as e:
                logger.warning(f"Jev decision call failed/timed out ({e}); falling back to deterministic rules.")
                backend = "rules"

        if backend == "rules":
            content_lower = message.content.lower()

            if receiver == "scribe":
                action = "deliver"
                confidence = 1.0

            elif message.to:
                if message.to == receiver or (message.mentions and receiver in message.mentions):
                    action = "deliver"
                    confidence = 0.98
                else:
                    action = "drop"
                    confidence = 0.92

            elif message.mentions and receiver in message.mentions:
                action = "deliver"
                confidence = 0.98

            elif receiver == "fe_worker" and any(k in content_lower for k in ["select *", "foreign key", "alter table", "drop table", "sql migration", "pragma", "create table"]):
                action = "drop"
                confidence = 0.88

            elif receiver == "be_worker" and any(k in content_lower for k in [":root", "padding-left", "font-family", "border-radius", "flex-direction"]) and "api" not in content_lower:
                action = "drop"
                confidence = 0.88

            elif "traceback (most recent call last)" in content_lower or content_lower.startswith("debug:"):
                action = "summarize"
                confidence = 0.85

            else:
                action = "deliver"
                confidence = 0.95

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        # Log decision into SQLite table delivery_decisions
        try:
            from sidecar.storage import get_storage
            get_storage().record_delivery_decision(
                run_id=run_id,
                message_id=message.id or "msg-unknown",
                receiver=receiver,
                action=action,
                confidence=confidence,
                backend=backend,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.debug(f"Failed to record delivery decision to SQLite: {e}")

        return {
            "action": action,
            "confidence": confidence,
            "backend": backend,
            "latency_ms": latency_ms,
        }

    def _query_jev(self, message: FeedMessage, receiver: str) -> Tuple[str, float]:
        """Optional query to Jev model API with 500ms timeout."""
        endpoint = os.environ.get("JEV_API_URL", "https://api.typesafe.ai/v1/decide")
        headers = {"Authorization": f"Bearer {os.environ.get('JEV_API_KEY')}"}
        import urllib.request
        import json
        payload = json.dumps({"message": message.content, "receiver": receiver, "task": "delivery_filter"}).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("action", "deliver"), float(data.get("confidence", 0.9))
