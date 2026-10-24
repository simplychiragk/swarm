"""
Smoke test CLI for LLM gateway.
Run with: python -m sidecar.llm.smoke "hello"
"""

import sys
import asyncio
from sidecar.llm import complete


async def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Hello Swarm"
    print(f"--- LLM Gateway Smoke Test ---")
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
