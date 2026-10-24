# Swarm Sidecar (FastAPI)

Agent orchestration, decision layer stub, and WebSocket broadcaster for Swarm.

## Requirements
- Python 3.10+
- Virtual environment (recommended)

## Setup & Running

1. **Activate / Create Virtual Environment (from repo root or `sidecar/`):**
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r sidecar/requirements.txt
   ```

3. **Start the Sidecar Server:**
   From the repository root (`swarm/`):
   ```bash
   python -m uvicorn sidecar.main:app --host 127.0.0.1 --port 8000 --reload
   ```

   Or set a custom port with `SWARM_SIDECAR_PORT`:
   ```bash
   $env:SWARM_SIDECAR_PORT="8000"
   python -m sidecar.main
   ```

## Endpoints

- `GET /health`: Heartbeat check (`{"status": "ok", "app": "swarm-sidecar"}`)
- `WS /ws`: WebSocket endpoint. Emits `EventEnvelope` (`feed_message`, `card_upsert`, `approval_request`). Automatically initiates the Section 9 demo scenario mock stream when a client connects.
- `POST /mock/start`: Manually trigger or re-run the mock scenario stream.
- `POST /mock/reset`: Stop mock stream and clear broadcast history.
- `POST /decision/route`: Route a task description to a lane (`FE`, `BE`, `DB`, `Design`, `Test`, `Docs`, `Ops`, `none`).
- `POST /decision/needs-approval`: Check if an action warrants user approval.
- `POST /decision/whiteboard-filter`: Filter whether an agent message generates a honeycomb whiteboard card.

## Decision Layer (Jev Stub)

Defined in [`sidecar/decision/`](./decision/):
- [`interface.py`](./decision/interface.py): Abstract protocol `DecisionLayer`.
- [`rule_engine.py`](./decision/rule_engine.py): Heuristic keyword & risk scoring fallback engine.
- Replace `RuleBasedDecisionLayer` with `JevDecisionLayer` when Jev API integration is ready.
