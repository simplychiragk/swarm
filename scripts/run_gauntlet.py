"""
CLI runner for Swarm Stage 13: The Gauntlet.
Executes autonomous multi-persona browser verification against a running Swarm sidecar,
asserts friction scores, and prints the path to the generated HTML audit report.

Usage:
    python scripts/run_gauntlet.py [--run-id RUN_ID] [--url URL] [--port PORT]
"""

import sys
import argparse
import urllib.request
import json


def main():
    parser = argparse.ArgumentParser(description="Swarm Gauntlet Persona Audit CLI")
    parser.add_argument("--run-id", default="run-default", help="Run ID to evaluate")
    parser.add_argument("--port", type=int, default=8000, help="Sidecar HTTP port")
    parser.add_argument("--url", default="", help="Optional custom target preview URL")
    args = parser.parse_args()

    preview_url = args.url or f"http://127.0.0.1:{args.port}/runs/{args.run_id}/preview/"
    endpoint = f"http://127.0.0.1:{args.port}/runs/{args.run_id}/gauntlet"

    print(f"==================================================")
    print(f"🛡️  SWARM GAUNTLET: MULTI-PERSONA AUDIT")
    print(f"==================================================")
    print(f"Target Run ID: {args.run_id}")
    print(f"Preview URL:   {preview_url}")
    print(f"Dispatching request to {endpoint}...\n")

    payload = json.dumps({"url": preview_url}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        grade = data.get("grade", "N/A")
        avg_friction = data.get("average_friction", 0.0)
        report_url = data.get("report_url", "")
        results = data.get("results", [])

        print(f"--------------------------------------------------")
        print(f"OVERALL GRADE:            {grade}")
        print(f"AVERAGE FRICTION SCORE:   {avg_friction} / 5.0")
        print(f"PERSONAS TESTED:          {len(results)}")
        print(f"--------------------------------------------------")

        for r in results:
            status = "PASS" if r.get("completed") else "FAIL"
            score = r.get("friction_score", 1)
            print(f"  • {r.get('name', 'Persona')}: [{status}] (Friction: {score}/5) - {r.get('archetype')}")
            for c in r.get("confusion_points", []):
                print(f"      - Note: {c}")

        print(f"\nReport generated at:")
        print(f"  http://127.0.0.1:{args.port}{report_url}")
        print(f"  http://127.0.0.1:{args.port}/runs/{args.run_id}/gauntlet/report")
        print(f"==================================================")
        sys.exit(0)

    except urllib.error.HTTPError as he:
        print(f"HTTP Error {he.code}: {he.read().decode('utf-8')}")
        sys.exit(1)
    except Exception as exc:
        print(f"Error running gauntlet: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
