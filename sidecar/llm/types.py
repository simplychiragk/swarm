"""
Data structures for the Swarm LLM Gateway.
"""

from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class LLMResult:
    """Standardized result returned by LLM gateway completion."""
    text: str
    parsed: Optional[Any]
    provider: str
    model: str
    latency_ms: float
