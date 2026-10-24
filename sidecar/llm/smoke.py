"""
Smoke test CLI for LLM gateway.
Run with:
    python -m sidecar.llm.smoke "hello"
    python -m sidecar.llm.smoke --all
"""

import sys
import time
import asyncio
import httpx
from sidecar.llm import complete, PROVIDER_CHAIN
from sidecar.llm.gateway import _call_provider_http
from sidecar.llm.mock_provider import mock_complete


async def test_all_providers(prompt: str):
    print("=== Testing All Configured Providers ===")
    test_messages = [
        {"role": "system", "content": "You are a concise AI assistant."},
        {"role": "user", "content": prompt},
    ]

    async with httpx.AsyncClient() as client:
        for provider in PROVIDER_CHAIN:
            if not provider.is_configured():
                print(f"[{provider.name:10s}] SKIPPED (Environment variable '{provider.api_key_env}' not set)")
                continue

            model = provider.get_model("fast")
            start = time.perf_counter()
            try:
                res = await _call_provider_http(
                    client=client,
                    provider=provider,
                    messages=test_messages,
                    tier="fast",
                    timeout=15.0,
                    json_mode=False,
                )
                latency = (time.perf_counter() - start) * 1000.0
                print(f"[{provider.name:10s}] OK (model: {model}, {latency:.1f}ms) -> {res[:60]}...")
            except Exception as e:
                latency = (time.perf_counter() - start) * 1000.0
                print(f"[{provider.name:10s}] FAILED ({latency:.1f}ms): {e}")

    # Always test deterministic mock
    start = time.perf_counter()
    mock_res = mock_complete(test_messages, tier="fast")
    latency = (time.perf_counter() - start) * 1000.0
    print(f"[{'mock':10s}] OK (model: mock-fast-v1, {latency:.1f}ms) -> {mock_res.text[:60]}...")
    print("=== Provider Test Complete ===")


async def main():
    args = sys.argv[1:]
    if "--all" in args:
        prompt = "Ping test for swarm hackathon"
        await test_all_providers(prompt)
        return

    prompt = args[0] if args else "Hello Swarm"
    print("--- LLM Gateway Smoke Test ---")
    print(f"Prompt: {prompt}")

    result = await complete(
        messages=[
            {"role": "system", "content": "You are a concise AI assistant."},
            {"role": "user", "content": prompt},
        ],
        tier="fast",
        timeout=10.0,
    )

    print(f"Provider : {result.provider}")
    print(f"Model    : {result.model}")
    print(f"Latency  : {result.latency_ms:.1f}ms")
    print(f"Output   : {result.text}")
    print("--- Smoke Test Successful ---")


if __name__ == "__main__":
    asyncio.run(main())

