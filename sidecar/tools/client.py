"""
TinyFish API Client.
Interfaces with TinyFish Search, Fetch, and Browser Agent execution.
Includes offline deterministic mock fallback for offline demo resilience.
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("swarm.tools.tinyfish")

SEARCH_ENDPOINT = "https://api.search.tinyfish.ai"
FETCH_ENDPOINT = "https://api.fetch.tinyfish.ai"
AGENT_ENDPOINT = "https://agent.tinyfish.ai/v1/run"  # TODO(verify-docs): verify exact REST path for remote agent execution


class TinyFishClient:
    """Client for TinyFish Web Search, Fetch, and Browser Agent execution."""

    def __init__(self, api_key: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("TINYFISH_API_KEY", "").strip()

    def is_live_configured(self) -> bool:
        """Returns True if a valid API key is set and mock mode is not requested."""
        if os.environ.get("SWARM_TINYFISH_MODE", "").lower() == "mock":
            return False
        return bool(self.api_key)

    async def search(self, query: str, purpose: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute web search query against TinyFish AI Search API.
        GET https://api.search.tinyfish.ai?query=...
        """
        if not self.is_live_configured():
            logger.info(f"TinyFish Search running in mock mode for query: '{query}'")
            return {
                "query": query,
                "results": [
                    {
                        "title": "Modern React Form Validation Patterns & Best Practices",
                        "url": "https://tinyfish.io/docs/react-form-patterns",
                        "snippet": "Use Zod schemas with pending state transitions for accessible, server-validated waitlist forms.",
                    },
                    {
                        "title": "FastAPI Request Validation with Pydantic v2",
                        "url": "https://fastapi.tiangolo.com/tutorial/body/",
                        "snippet": "Declare request bodies with Pydantic models for automatic JSON schema enforcement.",
                    },
                ],
            }

        async with httpx.AsyncClient() as client:
            headers = {
                "X-API-Key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
            }
            params = {"query": query}
            if purpose:
                params["purpose"] = purpose
            resp = await client.get(SEARCH_ENDPOINT, params=params, headers=headers, timeout=20.0)
            resp.raise_for_status()
            return resp.json()

    async def fetch(self, url: str) -> Dict[str, Any]:
        """
        Extract clean text content from target URL via TinyFish Fetch API.
        POST https://api.fetch.tinyfish.ai
        """
        if not self.is_live_configured():
            logger.info(f"TinyFish Fetch running in mock mode for URL: '{url}'")
            return {
                "url": url,
                "content": "Clean extracted HTML & text: React Form with CSRF tokens, responsive inputs, and email regex validator.",
                "status": "COMPLETED",
            }

        async with httpx.AsyncClient() as client:
            headers = {
                "X-API-Key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            # TODO(verify-docs): confirm JSON body shape for TinyFish fetch endpoint
            payload = {"url": url}
            resp = await client.post(FETCH_ENDPOINT, json=payload, headers=headers, timeout=20.0)
            resp.raise_for_status()
            return resp.json()

    async def run_browser_task(self, url: str, goal: str, sync: bool = True) -> Dict[str, Any]:
        """
        Automate real browser interaction via TinyFish Agent.
        POST https://agent.tinyfish.ai/v1/run
        """
        if not self.is_live_configured():
            logger.info(f"TinyFish Browser Agent running in mock mode for goal: '{goal}' on {url}")
            return {
                "run_id": "tf-browser-mock-42",
                "status": "COMPLETED",
                "result": {
                    "verdict": "PASS",
                    "details": "Browser agent navigated to waitlist page, entered test credentials ('Alex', 'alex@example.com', 'Dev'), and verified 201 response toast banner.",
                },
                "evidence": {
                    "kind": "screenshot",
                    "url_or_text": "https://tinyfish-artifacts.s3.amazonaws.com/evidence/waitlist-pass.png",
                },
                "num_of_steps": 4,
            }

        async with httpx.AsyncClient() as client:
            headers = {
                "X-API-Key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            # TODO(verify-docs): verify parameters for Agent REST run endpoint
            payload = {
                "url": url,
                "goal": goal,
                "sync": sync,
                "capture_screenshots": True,
            }
            resp = await client.post(AGENT_ENDPOINT, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            return resp.json()
