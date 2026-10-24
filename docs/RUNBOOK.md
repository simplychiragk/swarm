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

## 4. Resetting State

```powershell
# Reset WebSocket history and stop active runs
curl -X POST http://127.0.0.1:8000/mock/reset
```

---

## 5. Environment Variables Reference

| Variable | Purpose | Default | Required? |
|---|---|---|---|
| `SWARM_MODE` | Swarm orchestration mode (`mock` or `live`) | `mock` | No |
| `SWARM_SIDECAR_PORT` | HTTP & WebSocket server port | `8000` | No |
| `SWARM_LLM_MODE` | LLM gateway mode (`mock` or `live`) | `mock` | No |
| `NVIDIA_NIM_API_KEY` | Primary LLM provider key | `None` | Yes (for real LLM) |
| `OPENROUTER_API_KEY` | Secondary fallback LLM provider key | `None` | Optional |
| `BYOK_API_KEY` | Bring-Your-Own-Key provider key | `None` | Optional |
| `BYOK_BASE_URL` | Base URL for BYOK provider | `None` | Optional |
| `TINYFISH_API_KEY` | TinyFish Search, Fetch & Browser QA key | `None` | Optional (used in live tools) |

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
