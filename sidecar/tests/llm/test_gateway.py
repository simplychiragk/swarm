"""
Tests for Swarm LLM Gateway:
- Fallback order across providers
- 429 retry logic
- Timeout fall-through
- JSON schema repair prompt
- Deterministic mock mode
"""

import json
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from pydantic import BaseModel

from sidecar.llm.gateway import complete, health_tracker
from sidecar.llm.config import ProviderConfig


class SamplePlanSchema(BaseModel):
    tasks: list[dict]


class SampleQuestionSchema(BaseModel):
    question: str
    is_finished: bool


@pytest.fixture(autouse=True)
def reset_health():
    health_tracker.reset()
    yield
    health_tracker.reset()


@pytest.mark.asyncio
async def test_mock_mode_plain():
    """Verify mock mode returns deterministic response without API keys."""
    res = await complete(
        messages=[{"role": "user", "content": "Hello Queen"}],
        tier="fast",
    )
    assert res.provider == "mock"
    assert res.model == "mock-fast-v1"
    assert "Queen" in res.text or "Swarm" in res.text
    assert res.parsed is None


@pytest.mark.asyncio
async def test_mock_mode_structured_output():
    """Verify mock mode produces structured JSON adhering to Pydantic schema."""
    res = await complete(
        messages=[{"role": "user", "content": "Plan waitlist landing page"}],
        tier="fast",
        json_schema=SamplePlanSchema,
    )
    assert res.provider == "mock"
    assert isinstance(res.parsed, SamplePlanSchema)
    assert len(res.parsed.tasks) >= 2


@pytest.mark.asyncio
async def test_fallback_order():
    """Verify fallback from provider A (NVIDIA) to provider B (OpenRouter) on error."""
    mock_providers = [
        ProviderConfig("p1", "https://p1.ai", "K1", {"fast": "m1"}),
        ProviderConfig("p2", "https://p2.ai", "K2", {"fast": "m2"}),
    ]

    # Patch env and PROVIDER_CHAIN
    with patch("sidecar.llm.gateway.get_llm_mode", return_value="live"), \
         patch("sidecar.llm.gateway.PROVIDER_CHAIN", mock_providers), \
         patch.object(mock_providers[0], "is_configured", return_value=True), \
         patch.object(mock_providers[1], "is_configured", return_value=True), \
         patch.object(mock_providers[0], "get_api_key", return_value="k1"), \
         patch.object(mock_providers[1], "get_api_key", return_value="k2"):

        def mock_post(url, *args, **kwargs):
            if "p1.ai" in url:
                # Provider 1 returns 500 error
                req = httpx.Request("POST", url)
                resp = httpx.Response(500, request=req)
                raise httpx.HTTPStatusError("500 Server Error", request=req, response=resp)
            # Provider 2 succeeds
            req = httpx.Request("POST", url)
            return httpx.Response(
                200,
                request=req,
                json={"choices": [{"message": {"content": "Response from P2"}}]},
            )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
            res = await complete([{"role": "user", "content": "test"}], tier="fast")
            assert res.provider == "p2"
            assert res.text == "Response from P2"


@pytest.mark.asyncio
async def test_429_retry():
    """Verify gateway retries on HTTP 429 rate limit."""
    mock_provider = ProviderConfig("p1", "https://p1.ai", "K1", {"fast": "m1"})
    call_count = 0

    with patch("sidecar.llm.gateway.get_llm_mode", return_value="live"), \
         patch("sidecar.llm.gateway.PROVIDER_CHAIN", [mock_provider]), \
         patch.object(mock_provider, "is_configured", return_value=True), \
         patch.object(mock_provider, "get_api_key", return_value="k1"):

        def mock_post(url, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            req = httpx.Request("POST", url)
            if call_count == 1:
                resp = httpx.Response(429, request=req)
                raise httpx.HTTPStatusError("429 Rate Limit", request=req, response=resp)
            return httpx.Response(
                200,
                request=req,
                json={"choices": [{"message": {"content": "Success after retry"}}]},
            )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post), \
             patch("time.sleep", return_value=None):
            res = await complete([{"role": "user", "content": "retry test"}], tier="fast")
            assert res.provider == "p1"
            assert res.text == "Success after retry"
            assert call_count == 2


@pytest.mark.asyncio
async def test_timeout_fallthrough():
    """Verify gateway falls through to next provider when request times out."""
    mock_providers = [
        ProviderConfig("p_timeout", "https://timeout.ai", "K1", {"fast": "m1"}),
        ProviderConfig("p_backup", "https://backup.ai", "K2", {"fast": "m2"}),
    ]

    with patch("sidecar.llm.gateway.get_llm_mode", return_value="live"), \
         patch("sidecar.llm.gateway.PROVIDER_CHAIN", mock_providers), \
         patch.object(mock_providers[0], "is_configured", return_value=True), \
         patch.object(mock_providers[1], "is_configured", return_value=True), \
         patch.object(mock_providers[0], "get_api_key", return_value="k1"), \
         patch.object(mock_providers[1], "get_api_key", return_value="k2"):

        def mock_post(url, *args, **kwargs):
            if "timeout.ai" in url:
                raise httpx.TimeoutException("Read timed out")
            req = httpx.Request("POST", url)
            return httpx.Response(
                200,
                request=req,
                json={"choices": [{"message": {"content": "Backup responded"}}]},
            )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
            res = await complete([{"role": "user", "content": "timeout test"}], tier="fast")
            assert res.provider == "p_backup"
            assert res.text == "Backup responded"


@pytest.mark.asyncio
async def test_json_repair_retry():
    """Verify that malformed JSON triggers a repair prompt and recovery."""
    mock_provider = ProviderConfig("p1", "https://p1.ai", "K1", {"fast": "m1"})
    call_count = 0

    with patch("sidecar.llm.gateway.get_llm_mode", return_value="live"), \
         patch("sidecar.llm.gateway.PROVIDER_CHAIN", [mock_provider]), \
         patch.object(mock_provider, "is_configured", return_value=True), \
         patch.object(mock_provider, "get_api_key", return_value="k1"):

        def mock_post(url, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            req = httpx.Request("POST", url)
            if call_count == 1:
                # Broken JSON on first attempt
                return httpx.Response(
                    200,
                    request=req,
                    json={"choices": [{"message": {"content": "{broken json..."}}]},
                )
            # Repaired valid JSON on second attempt
            return httpx.Response(
                200,
                request=req,
                json={"choices": [{"message": {"content": json.dumps({"question": "Are you ready?", "is_finished": True})}}]},
            )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
            res = await complete(
                [{"role": "user", "content": "Need question"}],
                tier="fast",
                json_schema=SampleQuestionSchema,
            )
            assert res.provider == "p1"
            assert isinstance(res.parsed, SampleQuestionSchema)
            assert res.parsed.question == "Are you ready?"
            assert res.parsed.is_finished is True
            assert call_count == 2
