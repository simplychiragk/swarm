# Swarm Demo Script & Presenter Guide

**Scenario:** *"Build a landing page with a waitlist form"*  
**Event:** HackIIITD (Esya '26) Final Demo  
**Time Limit:** 2 - 3 minutes  

---

## 1. Demo Modes & Pre-Flight Check

Swarm provides three execution modes optimized for stage safety:

| Mode | Command / Environment | Behavior |
|---|---|---|
| **Live with Seeded Bug (Recommended)** | `$env:SWARM_DEMO_MODE="seeded_bug"; uvicorn sidecar.main:app` | Real LLM + live TinyFish browser QA. Intentionally seeds a disabled submit button; QA Bee catches it with evidence; Queen routes to FE Worker; FE Worker fixes it; QA re-tests and passes! |
| **Offline Golden Replay** | `$env:SWARM_DEMO_MODE="golden"; uvicorn sidecar.main:app` | 100% offline playback from `data/golden_run.json` with realistic pacing. Zero LLM calls, zero network calls, provenance tagged as `replay`. |
| **Deterministic Mock** | `$env:SWARM_MODE="mock"; uvicorn sidecar.main:app` | Deterministic mock scenario triggered automatically on UI connection. |

### Pre-Flight Verification
1. Verify Sidecar is healthy on `http://127.0.0.1:8000`:
   ```powershell
   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/health/deps
   ```
2. Launch the desktop app:
   ```powershell
   cd app; npm run tauri dev
   ```
3. Ensure the top status badge reads **CONNECTED** (green dot).

---

## 2. Step-by-Step Presenter Script (2 Minutes)

### 0:00 - 0:25 | The Hook & Goal Prompt
- **Presenter says:**
  > *"Traditional AI coding agents operate as opaque black boxes: you send a prompt, wait three minutes, and pray the code works without seeing the team's decisions or verifiable evidence. Swarm turns agent coding into a transparent, cooperative team sport where you watch and steer in real time."*
- **Action:** Type into prompt input:
  `Build a landing page with a waitlist form`
- **Screen Cue:**
  > *"Notice how the Queen immediately enters discovery mode—asking targeted questions to nail audience and constraints before writing a single line of code."*

### 0:25 - 0:50 | Queen Interview & Live Grounding (TinyFish)
- **Presenter says:**
  > *"Instead of hallucinating stale API patterns, our Research Bee uses TinyFish Search and Fetch to pull current 2026 design standards and schema patterns live from the web."*
- **Screen Cue:**
  > *"Look at the 'plan' channel and the Whiteboard: the Scribe just distilled 8 turns of chatter into a live Honeycomb card grounded in real-web TinyFish evidence."*

### 0:50 - 1:20 | Parallel Workers & Nectar Feed
- **Presenter says:**
  > *"Now watch our Frontend and Backend Workers collaborate in parallel. Notice they don't work in isolation—they talk across channels, sharing API schemas and component props."*
- **Screen Cue:**
  > *"Point at the Whiteboard: 'Notice the scribe just turned 14 agent messages into three clear cards: Backend API Route, Frontend Landing Page, and Live Grounding.' Meanwhile, real code is being written directly to the workspace."*

### 1:20 - 1:55 | QA Bee Browser Verification & Seeded-Bug Loop
- **Presenter says:**
  > *"Most coding tools claim code is done when the file is saved. Swarm refuses to call code done until our QA Bee tests it in a real browser using TinyFish."*
- **Screen Cue:**
  > *"Watch the QA bee run the real browser against our local preview. Notice the first test caught a disabled submit button! Watch what happens next: the Queen spots the failure evidence, routes it back to the Frontend Worker, the worker fixes the button, and QA re-tests and passes! A closed-loop fail, fix, and pass cycle right before your eyes."*

### 1:55 - 2:20 | Decision Layer & Approval Gate
- **Presenter says:**
  > *"Before any sensitive action reaches production, our Decision Layer stops execution. Deterministic policy rules ensure safety—no tool or command can bypass it."*
- **Screen Cue:**
  > *"Here is the approval gate stopping a deploy. Look at the Run Provenance & Verification Audit card on the board: it lists every tool call, its exact latency in milliseconds, and proof of whether it was a real live network call or simulated."*
- **Action:** Click **Approve**.
- **Screen Cue:**
  > *"The card turns green, Queen confirms live release, and our landing page is verified and shipped."*

---

## 3. Bulletproof Backup Plan (For Every Stage Failure Mode)

| Failure Mode | Built-In Defense | Immediate Presenter Action |
|---|---|---|
| **Wi-Fi Dies / Drops on Stage** | Golden Run replay mode (`data/golden_run.json`). Zero internet required. | Stop sidecar and run: `python scripts/run_golden.py` (works universally on CMD & PowerShell). The UI streams the exact verified run with full cards, chatter, and evidence. |
| **TinyFish API Timeout / 500** | Graceful fallback built into `TinyFishClient`. Returns deterministic mock payload tagged `simulated`. | No action needed! The pipeline catches it within 5s, tags the card evidence as `[SIMULATED]`, and proceeds without hanging. |
| **LLM Provider Outage (NIM 429/500)** | Gateway multi-provider fallback chain (NVIDIA -> OpenRouter -> BYOK -> Mock). | Automatic failover occurs in <1s. If all external APIs are unreachable, set `$env:SWARM_LLM_MODE="mock"` and restart sidecar. |
| **Browser Port Conflict** | Configurable via `SWARM_PORT` or `PORT`. | Run sidecar on alternative port e.g. `--port 8080` and point Tauri client config. |
| **Judge Asks 'Is this actually running or fake?'** | Provenance Audit Card (`card-provenance-summary`) and `/runs/{id}/permissions` endpoint. | Click the Audit Card on the Whiteboard: point to the latency numbers (e.g. `210ms`) and `[REAL]` provenance tags for TinyFish Search and Browser calls. Open `http://localhost:8000/runs/run-default/preview/` to show the real running page. |
