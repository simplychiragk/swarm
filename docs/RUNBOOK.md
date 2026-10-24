# Swarm Runbook

Comprehensive operational guide for running, configuring, testing, and debugging Swarm.

---

## 1. Setup from a Fresh Clone

```powershell
# Clone the repository
git clone https://github.com/simplychiragk/swarm.git
cd swarm

# Create root .env from template
Copy-Item .env.example .env

# Set up Python virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r sidecar/requirements.txt

# Install frontend dependencies
cd app
npm install
cd ..
```

---

## 2. Running Modes

### Mode A: Mock Mode (Default)
Runs entirely offline without requiring any API keys. Emits a realistic fake run of the Section 9 waitlist landing page scenario and responds to client messages.

```powershell
# Terminal 1: Sidecar (default SWARM_MODE=mock)
python -m uvicorn sidecar.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Desktop App
cd app
npm run tauri dev
```
*(Web-only preview alternative: `npm run dev` in `app/`, open `http://localhost:1420`)*.

---

### Mode B: Live Mode with Mock LLM
Runs live multi-agent orchestration while using deterministic offline LLM responses. No API keys needed.

```powershell
# Set environment variables in current shell
$env:SWARM_MODE="live"
$env:SWARM_LLM_MODE="mock"

# Terminal 1: Sidecar
python -m uvicorn sidecar.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Desktop App
cd app
npm run tauri dev
```

---

### Mode C: Live Mode with Real Keys
Runs real LLM inference through the provider fallback chain (NVIDIA NIM -> OpenRouter -> BYOK) and live TinyFish tools.

1. Edit `.env`:
   ```bash
   SWARM_MODE=live
   SWARM_LLM_MODE=live
   NVIDIA_NIM_API_KEY=your_nim_key
   OPENROUTER_API_KEY=your_openrouter_key
   TINYFISH_API_KEY=your_tinyfish_key
   ```
2. Start sidecar:
   ```powershell
   python -m uvicorn sidecar.main:app --host 127.0.0.1 --port 8000 --reload
   ```
3. Start Tauri app:
   ```powershell
   cd app
   npm run tauri dev
   ```

---

## 3. Running Tests

```powershell
# Run backend pytest suite
pytest sidecar/tests

# Run LLM gateway smoke test
python -m sidecar.llm.smoke "Hello Swarm"
```

---

## 4. Public Tunneling for TinyFish Remote Browser QA

The TinyFish remote browser agent executes in the cloud. To allow TinyFish to test locally built pages, expose port 8000 using any standard tunneling utility:

### Option A: LocalTunnel (No account required)
```powershell
npx localtunnel --port 8000
# Output: your url is: https://funny-otter-42.loca.lt
```

### Option B: Cloudflare Tunnel (cloudflared)
```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

### Option C: ngrok
```powershell
ngrok http 8000
```

### Configuring Swarm to use the Tunnel:
Set the tunnel URL in your environment before starting the sidecar:
```powershell
$env:SWARM_PREVIEW_URL="https://funny-otter-42.loca.lt"
```
QABee will automatically point the TinyFish remote browser agent to `https://funny-otter-42.loca.lt/runs/{id}/preview/` to execute real remote browser assertions and capture screenshots.

---

## 5. Seeded-Bug Demo Mode (Fail -> Fix -> Pass)

For live hackathon presentations and demos, you can activate the seeded-bug fail-fix-pass cycle:
```powershell
$env:SWARM_DEMO_MODE="seeded_bug"
$env:SWARM_PERMISSION_MODE="demo"
```
In this mode:
1. The Frontend Worker deliberately introduces a disabled submit button into `index.html`.
2. QABee tests the live preview, detects the disabled button, and reports `FAIL` with screenshot evidence.
3. The Queen identifies the failure, routes a fix task to `fe_worker` in channel `qa`.
4. `fe_worker` fixes `index.html` removing the disabled attribute.
5. QABee automatically re-tests, passes the assertion, and marks the task `PASS`.
6. Queen proceeds to the human release gate.

---

## 6. Autonomous Gauntlet Persona Audit

After a project is generated, you can launch 4 automated browser personas in parallel to stress-test UX, edge cases, and accessibility:

```powershell
# Run the Gauntlet against an active sidecar run
python scripts/run_gauntlet.py --run-id <run_id>
```

In this mode:
1. 4 personas execute in parallel under a concurrency limit:
   - **Impatient Mobile User**: Mobile viewport sizing and tap targets.
   - **Messy-Input User**: Unicode strings, emojis, plus-addressed email formatting.
   - **Double-Submit User**: Fast double-clicks and page refreshes.
   - **Malformed-Input User**: Boundary testing (>350 char strings, invalid emails).
2. Scribe publishes whiteboard cards for each persona with friction scores (1 to 5).
3. A self-contained, responsive HTML audit report is compiled and served at:
   `http://127.0.0.1:8000/runs/{run_id}/gauntlet/report`

---

## 7. Headless End-to-End Test Harnesses

To verify full integration without opening the browser or Tauri UI:

```powershell
# Offline mock integration test (< 5 seconds)
python scripts/e2e_mock.py

# Live integration test with real TinyFish API & browser verification (< 15 seconds)
python scripts/e2e_live.py
```

---

## 8. Resetting State

```powershell
# Reset WebSocket history and stop active runs
curl -X POST http://127.0.0.1:8000/mock/reset
```

---

## 9. Environment Variables Reference

| Variable | Purpose | Default | Required? |
|---|---|---|---|
| `SWARM_MODE` | Swarm orchestration mode (`mock` or `live`) | `mock` | No |
| `SWARM_DEMO_MODE` | Special demo mode (`seeded_bug` or `golden`) | `None` | No |
| `SWARM_PACING` | Agent action pacing (`real`, `fast`, or `instant`) | `real` | No |
| `SWARM_SIDECAR_PORT` | HTTP & WebSocket server port | `8000` | No |
| `SWARM_LLM_MODE` | LLM gateway mode (`mock` or `live`) | `mock` | No |
| `NVIDIA_NIM_API_KEY` | Primary LLM provider key | `None` | Yes (for real LLM) |
| `OPENROUTER_API_KEY` | Secondary fallback LLM provider key | `None` | Optional |
| `BYOK_API_KEY` | Bring-Your-Own-Key provider key | `None` | Optional |
| `BYOK_BASE_URL` | Base URL for BYOK provider | `None` | Optional |
| `TINYFISH_API_KEY` | TinyFish Search, Fetch & Browser QA key | `None` | Optional (used in live tools) |
| `SWARM_TINYFISH_MODE` | Force TinyFish mock mode (`mock` or `live`) | `live` (if key set) | No |
| `SWARM_PERMISSION_MODE` | Permission gating mode (`strict` or `demo`) | `strict` | No |
| `SWARM_DB_PATH` | Path to SQLite audit database | `workspace/swarm_audit.db` | No |
| `ENABLE_TINYFISH_BEES` | Enable ResearchBee and QABee in live engine | `false` | No |

---

## 6. Troubleshooting

### Problem: Sidecar will not start (`address already in use`)
- **Cause:** Another process is holding port 8000.
- **Fix:**
  ```powershell
  # Check which process is on port 8000
  netstat -ano | findstr :8000
  # Or use an alternate port:
  $env:SWARM_SIDECAR_PORT="8001"
  python -m uvicorn sidecar.main:app --host 127.0.0.1 --port 8001 --reload
  ```

### Problem: App displays "DISCONNECTED"
- **Cause:** Mismatch between frontend WebSocket target and sidecar listening address, or sidecar is stopped.
- **Fix:**
  - Verify sidecar is healthy: `curl http://127.0.0.1:8000/health`.
  - In the app UI header, verify the URL is `ws://127.0.0.1:8000/ws` or `ws://localhost:8000/ws`. On Windows, prefer `127.0.0.1` over `localhost` to avoid IPv6 resolution delays.

### Problem: Provider 429 or 5xx errors during live runs
- **Cause:** Upstream model provider rate limit or downtime.
- **Fix:** The LLM gateway automatically logs the failure and falls through from NVIDIA NIM to OpenRouter free models to BYOK. If all remote providers fail, fall back to offline mode by setting `SWARM_LLM_MODE=mock`.

### Problem: Agent actions hanging or timing out on approvals
- **Cause:** `SWARM_PERMISSION_MODE` defaults to `strict`, which pauses execution and waits up to 120 seconds for interactive user approval on `HIGH` and `MEDIUM` tier actions.
- **Fix:**
  - In the desktop UI, approve or redirect the pending action modal.
  - Or, grant `"run"` scope on the first prompt to auto-approve identical actions for the run.
  - For continuous demo runs (e.g. hackathon judging), set `SWARM_PERMISSION_MODE=demo` so `MEDIUM` actions (allowlisted commands, TinyFish fetch/browser tasks) are auto-approved.
