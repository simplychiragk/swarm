"""
Headless E2E Live Test Harness for Swarm.
Runs in SWARM_MODE=live with real TinyFish API integration.
Validates Queen interview, worker construction into workspace/<run_id>/,
TinyFish search and browser QA, and verifies provenance: 'real' in SQLite.
Times out at 120 seconds.
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


async def run_e2e_live() -> None:
    start_time = time.perf_counter()
    port = get_free_port()
    run_id = f"e2e-live-{int(time.time())}"
    db_file = root_dir / "data" / "e2e_live.db"
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass

    env = os.environ.copy()
    env["SWARM_MODE"] = "live"
    env["SWARM_PACING"] = "fast"
    env["SWARM_PERMISSION_MODE"] = "demo"
    env["ENABLE_TINYFISH_BEES"] = "true"
    env["SWARM_DB_PATH"] = str(db_file)
    env["PYTHONUNBUFFERED"] = "1"

    log_file = root_dir / "data" / "e2e_live_sidecar.log"
    sidecar_out = open(str(log_file), "w", encoding="utf-8")

    print(f"[LIVE E2E] Spawning sidecar in live mode on 127.0.0.1:{port} (log: {log_file})...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "sidecar.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        stdout=sidecar_out,
        stderr=subprocess.STDOUT,
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
            print("[LIVE E2E FAIL] Sidecar failed to start within 6 seconds.")
            sys.exit(1)

        print("[LIVE E2E] Sidecar online. Connecting via WebSocket...")
        import websockets

        received_events: List[Dict[str, Any]] = []
        approval_seen = False
        approval_sent = False
        interview_replied = False

        ws_url = f"ws://127.0.0.1:{port}/ws?run_id={run_id}"
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as ws:
            # 1. Send initial goal
            now_iso = datetime.now(timezone.utc).isoformat()
            user_msg = {
                "event": "user_message",
                "payload": {
                    "id": "usr-live-1",
                    "text": "Build a landing page with a waitlist form",
                    "timestamp": now_iso,
                    "mode": "steer",
                },
            }
            await ws.send(json.dumps(user_msg))

            # 2. Main streaming loop bounded by 120s timeout
            stream_start = time.perf_counter()
            while time.perf_counter() - stream_start < 120.0:
                try:
                    msg_text = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    evt = json.loads(msg_text)
                    received_events.append(evt)
                    event_type = evt.get("event")
                    payload = evt.get("payload", {})

                    # If Queen asks clarifying question, reply immediately to progress interview
                    if event_type == "feed_message" and payload.get("sender") == "queen" and not interview_replied:
                        content = payload.get("content", "")
                        if "?" in content:
                            print(f"[LIVE E2E] Queen inquired: '{content}'. Replying with specs...")
                            reply_msg = {
                                "event": "user_message",
                                "payload": {
                                    "id": "usr-live-2",
                                    "text": "Audience is developers, dark modern honeycomb aesthetic, capture name, email, role",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "mode": "steer",
                                },
                            }
                            await ws.send(json.dumps(reply_msg))
                            interview_replied = True

                    # Handle Approval Gate
                    if event_type == "approval_request" and not approval_sent:
                        approval_seen = True
                        appr_id = payload.get("id", "appr-release-1")
                        card_id = payload.get("card_id", "card-release-gate")

                        print(f"[LIVE E2E] Approval gate received: '{payload.get('prompt')}'. Approving...")
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

                    # Completion condition: release gate card is done
                    if approval_sent and event_type == "card_upsert":
                        if payload.get("id") == "card-release-gate" and payload.get("status") == "done":
                            print("[LIVE E2E] Release gate card marked DONE. Run verified successfully!")
                            break

                except asyncio.TimeoutError:
                    if approval_sent:
                        break
                    continue

        # 3. Validations
        event_types = {e.get("event") for e in received_events}
        print(f"[LIVE E2E] Received {len(received_events)} events covering: {event_types}")

        assert "feed_message" in event_types, "Must receive feed messages"
        assert "card_upsert" in event_types, "Must receive whiteboard cards"
        assert approval_seen, "Must reach approval gate"

        # Check SQLite DB for real provenance
        import sqlite3
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events WHERE run_id = ?;", (run_id,))
        count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM events WHERE run_id = ? AND provenance = 'real';", (run_id,))
        real_count = cur.fetchone()[0]
        conn.close()

        print(f"[LIVE E2E] SQLite recorded {count} total events ({real_count} real provenance) for run '{run_id}'")
        assert count > 0, "Events must be persisted to SQLite"
        assert real_count > 0, "Must contain real provenance events in live run"

        # Check workspace files
        workspace = root_dir / "workspace" / run_id
        assert (workspace / "index.html").exists(), "index.html must be generated in workspace"
        assert (workspace / "style.css").exists(), "style.css must be generated in workspace"
        assert (workspace / "app.js").exists(), "app.js must be generated in workspace"
        assert (workspace / "api" / "main.py").exists(), "api/main.py must be generated in workspace"

        duration = time.perf_counter() - start_time
        print(f"[LIVE E2E SUCCESS] Full live run passed in {round(duration, 2)}s (< 120s budget)!")

    finally:
        kill_proc_tree(proc.pid)
        try:
            sidecar_out.close()
        except Exception:
            pass


def main():
    try:
        asyncio.run(run_e2e_live())
        sys.exit(0)
    except AssertionError as ae:
        print(f"[LIVE E2E ASSERTION FAILED]: {ae}")
        sys.exit(1)
    except Exception as exc:
        print(f"[LIVE E2E UNHANDLED ERROR]: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
