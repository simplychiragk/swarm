# Swarm 🐝

> *A team of AI agents that builds with you, in the open.*

Built for HackIIITD (Esya '26) powered by TinyFish.

---

## Architecture Overview

Swarm decouples the user experience and agent farm into two coordinated layers:
- **`app/`**: Desktop client built with Tauri v2, React, TypeScript, and Vite. Displays the live Honeycomb Whiteboard and agent nectar feed.
- **`sidecar/`**: Python FastAPI backend with WebSockets broadcasting agent feed messages, whiteboard summaries (honey), and approval gates. Includes the rule-based Decision Layer stub (for Jev).
- **`shared/`**: JSON Schemas defining the core contracts (`FeedMessage`, `WhiteboardCard`, `ApprovalRequest`, `EventEnvelope`), with generated TypeScript types and Pydantic models.
- **`docs/`**: Project context ([`docs/SWARM_CONTEXT.md`](./docs/SWARM_CONTEXT.md)).

---

## Quick Start (Run Both Together)

### Prerequisites
- Node.js (v18+) & npm
- Python (3.10+)
- Rust & Cargo (for Tauri v2 desktop shell)

### 1. Start the FastAPI Sidecar
From the repository root:
```bash
# Optional: create & activate virtualenv
python -m venv .venv
.venv\Scripts\Activate.ps1    # On Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r sidecar/requirements.txt

# Run the sidecar server
python -m uvicorn sidecar.main:app --host 127.0.0.1 --port 8000 --reload
```
Sidecar runs at `http://127.0.0.1:8000`. Verify with `curl http://127.0.0.1:8000/health`.

### 2. Start the Tauri Desktop App
In a second terminal:
```bash
cd app
npm install
npm run tauri dev
```
*(If you just want to run the web frontend in your browser without compiling Tauri, run `npm run dev` in `app/` and visit `http://localhost:1420`)*.

### 3. Verify Live Streaming
As soon as the desktop window loads, it connects to `ws://localhost:8000/ws`. The sidecar immediately begins streaming the Section 9 Waitlist Landing Page mock scenario:
1. **Queen Discovery**: Queen asks target audience, style, and form fields.
2. **TinyFish Research**: Research bee fetches React form patterns with TinyFish Search.
3. **Parallel Construction**: Frontend and backend workers build and message live.
4. **Scribe Summaries**: Honeycomb whiteboard cards update with live progress.
5. **TinyFish Browser QA**: QA bee tests the form in a real browser session with attached evidence.
6. **Approval Gate**: Production release card flagged as `needs_approval`, issuing an `approval_request` event.

You can trigger additional runs anytime with:
```bash
curl -X POST http://127.0.0.1:8000/mock/start
```
Or reset history with:
```bash
curl -X POST http://127.0.0.1:8000/mock/reset
```

---

## Directory Structure

```text
swarm/
├── app/                  # Tauri v2 + React + Vite frontend (Tanmay's area)
│   ├── src/
│   │   ├── types/        # Mirror of shared TypeScript contracts
│   │   ├── App.tsx       # Live WebSocket raw JSON event listener
│   │   └── App.css       # Semantic styling with CSS variables & 8px grid
│   ├── src-tauri/        # Rust Tauri v2 shell configuration
│   └── package.json
├── sidecar/              # FastAPI agent sidecar & mock streamer
│   ├── decision/         # Decision layer interface & rule-based engine stub (Jev)
│   ├── models/           # Pydantic contract models
│   ├── broadcaster.py    # WebSocket connection manager & event replay
│   ├── mock_runner.py    # Section 9 waitlist landing page scenario generator
│   ├── main.py           # FastAPI app & endpoints (/health, /ws, /mock/*, /decision/*)
│   ├── requirements.txt
│   └── README.md
├── shared/               # Single source of truth contracts
│   ├── schemas/          # JSON Schemas (feed_message, whiteboard_card, etc.)
│   └── types/            # TypeScript interface definitions
├── docs/
│   └── SWARM_CONTEXT.md  # Single source of truth context & rules
└── README.md
```

---

## Contracts Reference

- **`FeedMessage`**: `{ id, timestamp, sender, lane, type, content, metadata? }`
  - `sender`: `queen` | `worker` | `scribe` | `qa` | `research` | `system`
  - `lane`: `FE` | `BE` | `DB` | `Design` | `Test` | `Docs` | `Ops` | `none`
  - `type`: `chat` | `task` | `status` | `evidence` | `error`
- **`WhiteboardCard`**: `{ id, title, summary, status, lane, evidence?, updated_at }`
  - `status`: `planned` | `in_progress` | `done` | `needs_approval` | `failed`
- **`EventEnvelope`**: `{ event: "feed_message" | "card_upsert" | "approval_request", payload }`
