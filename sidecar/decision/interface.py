"""
Decision Layer Interface.
Defines the contract for task routing, approval gating, and whiteboard filtering.
Jev model implementation will implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from sidecar.models.contracts import Lane, FeedMessage


class DecisionLayer(ABC):
    @abstractmethod
    def route_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Lane:
        """
        Routes a given task to the appropriate worker lane.
        """
        pass

    @abstractmethod
    def needs_approval(self, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determines whether a proposed action requires human sign-off.
        """
        pass

    @abstractmethod
    def should_show_on_whiteboard(self, message: FeedMessage) -> bool:
        """
        Filters raw agent messages (nectar) to determine if it should produce a whiteboard card (honey).
        """
        pass
