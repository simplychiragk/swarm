"""
Configuration for LLM Gateway providers and fallback chain.
Defines providers, endpoints, API key environment variables, and model tiers.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    models_by_tier: Dict[str, str]
    extra_headers: Dict[str, str] = field(default_factory=dict)

    def is_configured(self) -> bool:
        """Returns True if the required API key environment variable is populated."""
        return bool(os.environ.get(self.api_key_env, "").strip())

    def get_api_key(self) -> Optional[str]:
        return os.environ.get(self.api_key_env, "").strip() or None

    def get_model(self, tier: str) -> str:
        return self.models_by_tier.get(tier, self.models_by_tier.get("fast", ""))


# Priority-ordered provider fallback chain
PROVIDER_CHAIN: List[ProviderConfig] = [
    ProviderConfig(
        name="nvidia",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_NIM_API_KEY",
        models_by_tier={
            "fast": "meta/llama-3.1-8b-instruct",
            "smart": "meta/llama-3.3-70b-instruct",
        },
    ),
    ProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        models_by_tier={
            "fast": "meta-llama/llama-3.3-70b-instruct:free",
            "smart": "meta-llama/llama-3.3-70b-instruct:free",
        },
        extra_headers={
            "HTTP-Referer": "https://github.com/simplychiragk/swarm",
            "X-Title": "Swarm Hackathon",
        },
    ),
    ProviderConfig(
        name="byok",
        base_url=os.environ.get("BYOK_BASE_URL", "https://api.openai.com/v1"),
        api_key_env="BYOK_API_KEY",
        models_by_tier={
            "fast": os.environ.get("BYOK_MODEL_FAST", "gpt-4o-mini"),
            "smart": os.environ.get("BYOK_MODEL_SMART", "gpt-4o"),
        },
    ),
]


def get_llm_mode() -> str:
    """Returns 'mock' or 'live'. Defaults to 'mock' for offline reliability."""
    return os.environ.get("SWARM_LLM_MODE", "mock").strip().lower()


def get_available_providers() -> List[ProviderConfig]:
    """Returns providers from the fallback chain that have API keys present in the environment."""
    return [p for p in PROVIDER_CHAIN if p.is_configured()]
