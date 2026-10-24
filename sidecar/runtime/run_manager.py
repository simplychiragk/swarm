"""
Abstract RunManager interface and default no-op implementation.
Manages the orchestration lifecycle of a live agent run.
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging
from sidecar.models.contracts import UserMessage, ApprovalResponse

logger = logging.getLogger("swarm.runtime.run_manager")


class RunManager(ABC):
    """Abstract manager orchestrating a multi-agent run."""

    @abstractmethod
    async def start_run(self, user_text: str) -> None:
        """Initiate a new swarm run based on an initial user prompt."""
        pass

    @abstractmethod
    async def handle_user_message(self, message: UserMessage) -> None:
        """Handle an inbound user message during an ongoing run."""
        pass

    @abstractmethod
    async def handle_approval(self, response: ApprovalResponse) -> None:
        """Handle a client approval decision (approve or redirect)."""
        pass


class NoOpRunManager(RunManager):
    """Default no-op implementation of RunManager."""

    async def start_run(self, user_text: str) -> None:
        logger.info(f"NoOpRunManager: start_run received '{user_text}' (no-op)")

    async def handle_user_message(self, message: UserMessage) -> None:
        logger.info(f"NoOpRunManager: handle_user_message received '{message.text}' (no-op)")

    async def handle_approval(self, response: ApprovalResponse) -> None:
        logger.info(f"NoOpRunManager: handle_approval received decision '{response.decision}' for card {response.card_id} (no-op)")
