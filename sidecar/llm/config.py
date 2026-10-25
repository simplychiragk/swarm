"""
Configuration for LLM Gateway providers and fallback chain.
Defines providers, endpoints, API key environment variables, and model tiers.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    models_by_tier: Dict[str, str]
    extra_headers: Dict[str, str] = field(default_factory=dict)

    def is_configured(self) -> bool:
        """Returns True if the required API key environment variable is populated or provider supports keyless public mode."""
        if self.name == "pollinations":
            return True
        return bool(os.environ.get(self.api_key_env, "").strip())

    def get_api_key(self) -> Optional[str]:
        return os.environ.get(self.api_key_env, "").strip() or None

    def get_model(self, tier: str) -> str:
        return self.models_by_tier.get(tier, self.models_by_tier.get("fast", ""))


# Priority-ordered provider fallback chain
PROVIDER_CHAIN: List[ProviderConfig] = [
    ProviderConfig(
        name="pollinations",
        base_url=os.environ.get("POLLINATIONS_BASE_URL", "https://gen.pollinations.ai/v1"),
        api_key_env="POLLINATIONS_API_KEY",
        models_by_tier={
            "fast": os.environ.get("POLLINATIONS_MODEL_FAST", "openai/gpt-5.4-nano"),
            "smart": os.environ.get("POLLINATIONS_MODEL_SMART", "openai/gpt-5.4-nano"),
        },
    ),
    ProviderConfig(
        name="nvidia",
        base_url=os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key_env="NVIDIA_NIM_API_KEY",
        models_by_tier={
            "fast": os.environ.get("NVIDIA_MODEL_FAST", "meta/llama-3.1-8b-instruct"),
            "smart": os.environ.get("NVIDIA_MODEL_SMART", "meta/llama-3.3-70b-instruct"),
        },
    ),
    ProviderConfig(
        name="openrouter",
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key_env="OPENROUTER_API_KEY",
        models_by_tier={
            "fast": os.environ.get("OPENROUTER_MODEL_FAST", "openai/gpt-5.4-nano"),
            "smart": os.environ.get("OPENROUTER_MODEL_SMART", "openai/gpt-5.4-nano"),
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


def update_provider_config(
    name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    smart_model: Optional[str] = None,
    fast_model: Optional[str] = None,
) -> None:
    """Updates provider configuration at runtime dynamically."""
    for provider in PROVIDER_CHAIN:
        if provider.name == name:
            if base_url:
                provider.base_url = base_url
            if smart_model:
                provider.models_by_tier["smart"] = smart_model
            if fast_model:
                provider.models_by_tier["fast"] = fast_model
            if api_key:
                os.environ[provider.api_key_env] = api_key
            break


def validate_startup_config() -> List[str]:
    """
    Validates LLM configuration at startup and returns user-friendly advisory messages.
    """
    mode = get_llm_mode()
    warnings = []
    if mode == "live":
        available = get_available_providers()
        if not available:
            warnings.append(
                "SWARM_LLM_MODE is set to 'live' but no LLM provider API keys were detected "
                "(POLLINATIONS_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY, or BYOK_API_KEY). "
                "The gateway will fall back to offline deterministic mock mode."
            )
        else:
            names = [p.name for p in available]
            warnings.append(f"Live LLM mode active. Configured providers: {', '.join(names)}")
    else:
        warnings.append("LLM running in offline deterministic mock mode (SWARM_LLM_MODE=mock).")
    return warnings
