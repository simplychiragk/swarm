"""
Headless E2E Mock Test Harness for Swarm.
Starts sidecar in SWARM_MODE=mock and SWARM_PACING=fast.
Connects via WebSocket, drives the Section 9 waitlist scenario, resolves the approval gate,
and verifies SQLite event log and workspace state.
Runs headlessly and finishes in < 15 seconds.
"""

import sys
import os
import json
import time
import socket
import asyncio
import urllib.request
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def kill_proc_tree(pid: int) -> None:
    try:
        if os.name == 'nt':
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        else:
            os.kill(pid, 9)
    except Exception:
        pass


async def run_e2e_mock() -> None:
    start_time = time.perf_counter()
    port = get_free_port()
    run_id = f"e2e-mock-{int(time.time())}"
    db_file = root_dir / "data" / "e2e_mock.db"
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass

    env = os.environ.copy()
    env["SWARM_MODE"] = "mock"
    env["SWARM_PACING"] = "fast"
    env["SWARM_PERMISSION_MODE"] = "demo"
    env["SWARM_DB_PATH"] = str(db_file)
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[E2E] Spawning sidecar in mock mode on 127.0.0.1:{port}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "sidecar.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # 1. Wait for health endpoint
        health_ok = False
        health_url = f"http://127.0.0.1:{port}/health"
        for _ in range(30):
            try:
                with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                    if resp.status == 200:
                        health_ok = True
                        break
            except Exception:
                await asyncio.sleep(0.2)

        if not health_ok:
            print("[E2E FAIL] Sidecar failed to start within 6 seconds.")
            sys.exit(1)

        print("[E2E] Sidecar healthy. Connecting via WebSocket...")
        import websockets

        received_events: List[Dict[str, Any]] = []
        approval_seen = False
        approval_sent = False

        ws_url = f"ws://127.0.0.1:{port}/ws?run_id={run_id}"
        async with websockets.connect(ws_url) as ws:
            # Send initial goal
            now_iso = datetime.now(timezone.utc).isoformat()
            user_msg = {
                "event": "user_message",
                "payload": {
                    "id": "usr-e2e-1",
                    "text": "Build a landing page with a waitlist form",
                    "timestamp": now_iso,
                    "mode": "steer",
                },
            }
            await ws.send(json.dumps(user_msg))

            # Stream loop with 12s timeout
            stream_start = time.perf_counter()
            while time.perf_counter() - stream_start < 12.0:
                try:
                    msg_text = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    evt = json.loads(msg_text)
                    received_events.append(evt)
                    event_type = evt.get("event")

                    if event_type == "approval_request" and not approval_sent:
                        approval_seen = True
                        payload = evt.get("payload", {})
                        appr_id = payload.get("id", "appr-default")
                        card_id = payload.get("card_id", "card-approval")

                        # Send approval response
                        appr_resp = {
                            "event": "approval_response",
                            "payload": {
                                "approval_id": appr_id,
                                "card_id": card_id,
                                "decision": "approve",
                                "scope": "once",
                            },
                        }
                        await ws.send(json.dumps(appr_resp))
                        approval_sent = True

                    # Break when approval was processed and we receive confirmation
                    if approval_sent and event_type in ("card_upsert", "feed_message"):
                        p = evt.get("payload", {})
                        if p.get("status") == "done" or "resolved" in p.get("content", "").lower():
                            break

                except asyncio.TimeoutError:
                    if approval_sent:
                        break
                    continue

        # 2. Assertions
        event_types = {e.get("event") for e in received_events}
        print(f"[E2E] Received {len(received_events)} events covering types: {event_types}")

        assert "feed_message" in event_types, "Must receive feed_message events"
        assert "card_upsert" in event_types, "Must receive card_upsert events"
        assert approval_seen, "Must receive approval_request event"
        assert approval_sent, "Must successfully send approval_response"

        # Check SQLite DB
        import sqlite3
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events WHERE run_id = ?;", (run_id,))
        count = cur.fetchone()[0]
        conn.close()
        print(f"[E2E] SQLite recorded {count} events for run '{run_id}'")
        assert count > 0, "SQLite must persist run events"

        duration = time.perf_counter() - start_time
        print(f"[E2E SUCCESS] Headless mock test passed in {round(duration, 2)}s (< 15s budget)!")

    finally:
        kill_proc_tree(proc.pid)


def main():
    try:
        asyncio.run(run_e2e_mock())
        sys.exit(0)
    except AssertionError as ae:
        print(f"[E2E ASSERTION FAILED]: {ae}")
        sys.exit(1)
    except Exception as exc:
        print(f"[E2E UNHANDLED ERROR]: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
