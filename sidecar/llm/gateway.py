"""
Core LLM Gateway.
Provides multi-provider fallback execution, retries, cooldowns, and structured JSON output.
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional, Union, Type
import httpx
from pydantic import BaseModel, ValidationError

from .types import LLMResult
from .config import (
    ProviderConfig,
    PROVIDER_CHAIN,
    get_llm_mode,
)
from .mock_provider import mock_complete

logger = logging.getLogger("swarm.llm.gateway")


class ProviderHealthTracker:
    """Tracks provider failures and imposes cooldown windows after repeated failures."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._consecutive_failures: Dict[str, int] = {}
        self._cooldown_until: Dict[str, float] = {}

    def is_available(self, provider_name: str) -> bool:
        now = time.time()
        cooldown = self._cooldown_until.get(provider_name, 0.0)
        if now < cooldown:
            return False
        return True

    def record_success(self, provider_name: str):
        self._consecutive_failures[provider_name] = 0
        self._cooldown_until.pop(provider_name, None)

    def record_failure(self, provider_name: str, reason: str):
        count = self._consecutive_failures.get(provider_name, 0) + 1
        self._consecutive_failures[provider_name] = count
        logger.warning(f"Provider '{provider_name}' failure #{count}: {reason}")
        if count >= self.failure_threshold:
            self._cooldown_until[provider_name] = time.time() + self.cooldown_seconds
            logger.warning(
                f"Provider '{provider_name}' exceeded {self.failure_threshold} failures. Cooling down for {self.cooldown_seconds}s."
            )

    def reset(self):
        self._consecutive_failures.clear()
        self._cooldown_until.clear()


health_tracker = ProviderHealthTracker()


def _format_schema_instruction(json_schema: Any) -> str:
    if isinstance(json_schema, dict):
        return json.dumps(json_schema)
    if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
        return json.dumps(json_schema.model_json_schema())
    return "{}"


def _validate_structured_output(text: str, json_schema: Any) -> Any:
    """Validates raw text against the requested schema, returning the parsed object."""
    data = json.loads(text.strip())
    if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
        return json_schema.model_validate(data)
    return data


async def _call_provider_http(
    client: httpx.AsyncClient,
    provider: ProviderConfig,
    messages: List[Dict[str, str]],
    tier: str,
    timeout: float,
    json_mode: bool,
) -> str:
    """Dispatches a single HTTP chat completion to an OpenAI-compatible provider."""
    model = provider.get_model(tier)
    url = f"{provider.base_url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {provider.get_api_key()}",
        "Content-Type": "application/json",
    }
    headers.update(provider.extra_headers)

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    resp = await client.post(url, json=payload, headers=headers, timeout=timeout)

    if resp.status_code == 429:
        raise httpx.HTTPStatusError("Rate limited (429)", request=resp.request, response=resp)
    if resp.status_code >= 500:
        raise httpx.HTTPStatusError(f"Server error ({resp.status_code})", request=resp.request, response=resp)

    resp.raise_for_status()
    result = resp.json()

    choices = result.get("choices", [])
    if not choices:
        raise ValueError("Provider returned response with no choices")

    content = choices[0].get("message", {}).get("content", "")
    if not content or not content.strip():
        raise ValueError("Provider returned empty content")

    return content.strip()


async def complete(
    messages: List[Dict[str, str]],
    *,
    tier: str = "fast",
    json_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
    timeout: float = 30.0,
) -> LLMResult:
    """
    Public entry point for LLM gateway completion.

    Args:
        messages: List of message dictionaries with 'role' and 'content'.
        tier: 'fast' or 'smart' model tier.
        json_schema: Optional Pydantic model class or JSON schema dict for structured output.
        timeout: Per-request timeout in seconds.

    Returns:
        LLMResult with raw text, parsed structure (if json_schema), provider, model, and latency.
    """
    start_time = time.perf_counter()

    # If mock mode is requested or no live providers are configured, route to mock provider
    mode = get_llm_mode()
    configured_providers = [p for p in PROVIDER_CHAIN if p.is_configured()]

    if mode == "mock" or not configured_providers:
        if mode != "mock" and not configured_providers:
            logger.info("No provider API keys configured in environment. Falling back to mock LLM provider.")
        result = mock_complete(messages, tier=tier, json_schema=json_schema)
        # If schema is a Pydantic model, ensure parsed is an instance
        if json_schema and isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            if isinstance(result.parsed, dict):
                result.parsed = json_schema.model_validate(result.parsed)
        return result

    # Prepare messages if structured JSON output is requested
    active_messages = list(messages)
    if json_schema is not None:
        schema_text = _format_schema_instruction(json_schema)
        system_instruction = (
            f"You MUST return valid JSON adhering strictly to this JSON schema: {schema_text}. "
            "Do NOT include markdown formatting or backticks, return raw JSON only."
        )
        if active_messages and active_messages[0].get("role") == "system":
            active_messages[0] = {
                "role": "system",
                "content": f"{active_messages[0]['content']}\n\n{system_instruction}",
            }
        else:
            active_messages.insert(0, {"role": "system", "content": system_instruction})

    # Iterate through fallback chain
    async with httpx.AsyncClient() as client:
        for provider in configured_providers:
            if not health_tracker.is_available(provider.name):
                logger.info(f"Skipping provider '{provider.name}' (in cooldown)")
                continue

            # Attempt provider execution with up to 2 retries on 429
            max_attempts = 2
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(
                        f"Dispatching LLM request to provider '{provider.name}' (model: {provider.get_model(tier)}, attempt {attempt})"
                    )
                    content = await _call_provider_http(
                        client=client,
                        provider=provider,
                        messages=active_messages,
                        tier=tier,
                        timeout=timeout,
                        json_mode=(json_schema is not None),
                    )

                    # Validate structured output if schema requested
                    parsed_output = None
                    if json_schema is not None:
                        try:
                            parsed_output = _validate_structured_output(content, json_schema)
                        except (json.JSONDecodeError, ValidationError, ValueError) as parse_err:
                            logger.warning(f"Structured output validation failed ({parse_err}). Attempting repair prompt.")
                            repair_messages = list(active_messages) + [
                                {"role": "assistant", "content": content},
                                {
                                    "role": "user",
                                    "content": f"The response was invalid JSON or failed schema validation: {parse_err}. Return ONLY valid JSON conforming to the schema.",
                                },
                            ]
                            content = await _call_provider_http(
                                client=client,
                                provider=provider,
                                messages=repair_messages,
                                tier=tier,
                                timeout=timeout,
                                json_mode=True,
                            )
                            parsed_output = _validate_structured_output(content, json_schema)

                    health_tracker.record_success(provider.name)
                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    return LLMResult(
                        text=content,
                        parsed=parsed_output,
                        provider=provider.name,
                        model=provider.get_model(tier),
                        latency_ms=round(latency_ms, 2),
                    )

                except httpx.HTTPStatusError as http_err:
                    if http_err.response.status_code == 429 and attempt < max_attempts:
                        logger.warning(f"Provider '{provider.name}' returned 429 rate limit. Retrying in 1.5s...")
                        time.sleep(1.5)
                        continue
                    health_tracker.record_failure(provider.name, f"HTTP {http_err.response.status_code}")
                    break  # Fall through to next provider

                except (httpx.TimeoutException, httpx.RequestError, ValueError) as net_err:
                    health_tracker.record_failure(provider.name, str(net_err))
                    break  # Fall through to next provider

            logger.warning(f"Falling through from provider '{provider.name}' to next in chain.")

    # If all configured remote providers fail, fall back to offline mock completion as safeguard
    logger.error("All configured LLM providers failed or in cooldown. Falling back to deterministic mock completion.")
    fallback_res = mock_complete(messages, tier=tier, json_schema=json_schema)
    if json_schema and isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
        if isinstance(fallback_res.parsed, dict):
            fallback_res.parsed = json_schema.model_validate(fallback_res.parsed)
    return fallback_res
