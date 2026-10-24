# Swarm Demo Script

**Scenario:** *"Build a landing page with a waitlist form"*  
**Event:** HackIIITD (Esya '26) Final Demo

---

## Pre-Flight Check

1. Verify Sidecar is running on `http://127.0.0.1:8000`:
   ```bash
   curl http://127.0.0.1:8000/health
   ```
2. Open the desktop app (Tauri):
   ```bash
   cd app && npm run tauri dev
   ```
3. Ensure the top status badge reads **CONNECTED** (green dot).

---

## Step-by-Step Presentation Script

### Step 1: The Pitch & Prompt (0:00 - 0:30)
- **Speaker:** *"Traditional AI coding agents operate in a black box. You prompt them, wait minutes, and pray the code works without seeing decisions or verified evidence. Swarm turns agent coding into a transparent team sport."*
- **Action:** Enter initial prompt in UI:
  `"Build a landing page with a waitlist form."`

### Step 2: Queen Interview & Planning (0:30 - 1:00)
- **Audience sees:**
  - Queen Agent asks clarifying questions in the live feed.
  - Whiteboard card `"Discovery & Goal Definition"` appears in progress.
  - User submits answers: *"Audience is indie developers, dark modern honeycomb theme, capture name, email, and role."*
  - Queen finishes discovery and emits structured tasks with lane tags (`FE`, `BE`, `Test`, `Ops`).
  - Cards update on the whiteboard to `planned`.

### Step 3: Parallel Worker Construction & Peer Chatter (1:00 - 1:45)
- **Audience sees:**
  - Backend Worker and Frontend Worker activate simultaneously in the nectar feed.
  - BE Worker scaffolds `POST /api/waitlist` and broadcasts the API schema directly to the FE Worker.
  - FE Worker acknowledges the contract and outlines the React + Tailwind hero components matching the schema.
  - Scribe Agent batches chatter and posts human-readable card updates (`"Backend API Route"`, `"Frontend Landing Page"`) as `done`.

### Step 4: TinyFish Live-Web & Browser QA Verification (1:45 - 2:15)
- **Audience sees:**
  - QA Bee launches a real browser test via TinyFish.
  - The form is filled and submitted in an automated session.
  - The Whiteboard card updates with attached evidence:
    - Evidence tag: Screenshot artifact URL.
    - Evidence tag: 3 assertions passed (201 status, toast confirmed).

### Step 5: Decision Layer Approval Gate (2:15 - 2:45)
- **Audience sees:**
  - The Decision Layer flags production deployment as an external-facing high-risk action.
  - An interactive modal / card `"Production Release Gate"` appears with status `needs_approval`.
  - Buttons appear: **Approve & Deploy Live** / **Redirect**.
- **Action:** Click **Approve**.
- **Result:** The card turns to `done` (green checkmark), Queen confirms live release, and the run finishes.

---

## Fallback & Recovery Plan

If external networks or LLM providers fail during the live presentation, execute these fallbacks immediately:

1. **Provider Downtime (LLM 429/500):**
   - The LLM Gateway will automatically fall through NVIDIA NIM -> OpenRouter -> Mock.
   - If completely offline, set `SWARM_LLM_MODE=mock` in `.env` and restart sidecar. The full agent orchestration runs deterministically.

2. **Network Disruption during Presentation:**
   - Switch sidecar to `SWARM_MODE=mock`.
   - Re-trigger the full scripted demo instantly:
     ```bash
     curl -X POST http://127.0.0.1:8000/mock/start
     ```
   - The app UI will immediately display the streaming waitlist scenario without requiring external internet access.
