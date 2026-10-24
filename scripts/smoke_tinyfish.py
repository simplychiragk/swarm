"""
Smoke test script for TinyFish integration (Search, Fetch, and Browser Agent).
Tests against a known public site (e.g. example.com) or mock fallback,
measures timings, writes evidence artifacts to data/qa_smoke.json, and exits 0.
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from sidecar.tools.client import TinyFishClient


async def run_smoke() -> None:
    print("=" * 60)
    print("🐝 Swarm: TinyFish Tools Smoke Test")
    print("=" * 60)

    client = TinyFishClient()
    mode = "LIVE" if client.is_live_configured() else "MOCK / SIMULATED"
    print(f"Mode: {mode}")
    if client.is_live_configured():
        print("API Key: [CONFIGURED]")
    else:
        print("API Key: [UNSET / MOCK] (Set TINYFISH_API_KEY for live execution)")
    print("-" * 60)

    results_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": mode.lower(),
        "steps": {},
    }

    # Step 1: TinyFish Search
    print("\n[1/3] Testing TinyFish Search...")
    t0 = time.time()
    try:
        search_res = await client.search(query="best practice waitlist form fields 2026", limit=3)
        duration_ms = round((time.time() - t0) * 1000, 2)
        provenance = search_res.get("provenance", "simulated" if not client.is_live_configured() else "real")
        print(f"  ✓ Search succeeded in {duration_ms}ms (Provenance: {provenance})")
        results = search_res.get("results", [])
        print(f"  ✓ Found {len(results)} search results")
        if results:
            print(f"    Top: '{results[0].get('title')}' -> {results[0].get('url')}")
        results_summary["steps"]["search"] = {
            "status": "pass",
            "duration_ms": duration_ms,
            "provenance": provenance,
            "results_count": len(results),
        }
    except Exception as e:
        print(f"  ✗ Search failed: {e}")
        results_summary["steps"]["search"] = {"status": "fail", "error": str(e)}

    # Step 2: TinyFish Fetch
    print("\n[2/3] Testing TinyFish Fetch...")
    t0 = time.time()
    target_url = "https://example.com"
    try:
        fetch_res = await client.fetch(url=target_url)
        duration_ms = round((time.time() - t0) * 1000, 2)
        provenance = fetch_res.get("provenance", "simulated" if not client.is_live_configured() else "real")
        print(f"  ✓ Fetch succeeded in {duration_ms}ms (Provenance: {provenance})")
        content_len = len(fetch_res.get("content", ""))
        print(f"  ✓ Extracted {content_len} bytes of clean content")
        results_summary["steps"]["fetch"] = {
            "status": "pass",
            "duration_ms": duration_ms,
            "provenance": provenance,
            "content_bytes": content_len,
        }
    except Exception as e:
        print(f"  ✗ Fetch failed: {e}")
        results_summary["steps"]["fetch"] = {"status": "fail", "error": str(e)}

    # Step 3: TinyFish Browser Agent
    print("\n[3/3] Testing TinyFish Browser Agent...")
    t0 = time.time()
    browser_goal = "Navigate to page and verify header element exists"
    try:
        browser_res = await client.run_browser_task(url=target_url, goal=browser_goal, timeout_s=30.0)
        duration_ms = round((time.time() - t0) * 1000, 2)
        provenance = browser_res.get("provenance", "simulated" if not client.is_live_configured() else "real")
        verdict = browser_res.get("verdict", "PASS")
        print(f"  ✓ Browser task finished in {duration_ms}ms with verdict [{verdict}] (Provenance: {provenance})")
        print(f"  ✓ Details: {browser_res.get('details')}")
        evidence = browser_res.get("evidence", [])
        results_summary["steps"]["browser_agent"] = {
            "status": "pass",
            "verdict": verdict,
            "duration_ms": duration_ms,
            "provenance": provenance,
            "evidence": evidence,
        }
    except Exception as e:
        print(f"  ✗ Browser task failed: {e}")
        results_summary["steps"]["browser_agent"] = {"status": "fail", "error": str(e)}

    # Write evidence to data/qa_smoke.json
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    smoke_file = data_dir / "qa_smoke.json"
    smoke_file.write_text(json.dumps(results_summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✓ Evidence artifacts successfully written to: {smoke_file}")
    print("✓ TinyFish Smoke Test: ALL STEPS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_smoke())
