# Swarm Development Progress Log

## Status Overview

| Stage | Description | Status |
|---|---|---|
| Stage 1 | Contract bidirectional extensions, SWARM_MODE handling & RunManager interface | done |
| Stage 2 | LLM Gateway with provider fallback chain, JSON schemas & tests | planned |
| Stage 3 | Multi-agent engine (Queen, Workers, Scribe) on async message bus | planned |
| Stage 4 | TinyFish Search, Fetch & Browser QA tools integration | planned |

---

## Stage 1: Bidirectional Contracts, Runtime Manager & Dual Mode

### 1. What Was Built
- Extended shared contracts with client-to-server direction: `user_message` and `approval_response`.
- Updated JSON Schemas in `shared/schemas/` (`user_message.json`, `approval_response.json`, and updated `event_envelope.json`).
- Updated TypeScript types in `shared/types/contracts.ts` and `app/src/types/contracts.ts`.
- Updated Pydantic models in `sidecar/models/contracts.py` with `InboundEnvelope` validation and parsing helpers.
- Introduced `SWARM_MODE=mock|live` (default: `mock`). In live mode, the mock runner does not auto-start.
- In mock mode, the WebSocket server now actively responds to client messages:
  - `user_message` generates a canned Queen confirmation message.
  - `approval_response` updates the target whiteboard card to `done` (if approved) or `failed` (if redirected) and broadcasts the update.
- Created `sidecar/runtime/run_manager.py` with abstract `RunManager` and default `NoOpRunManager`.
- Created root `.env.example` documenting all configuration keys.
- Authored `docs/CONTRACT.md` and initial `docs/RUNBOOK.md`.

### 2. Files Added or Changed
- Added:
  - `shared/schemas/user_message.json`
  - `shared/schemas/approval_response.json`
  - `sidecar/runtime/__init__.py`
  - `sidecar/runtime/run_manager.py`
  - `.env.example`
  - `docs/CONTRACT.md`
  - `docs/RUNBOOK.md`
  - `docs/PROGRESS.md`
- Changed:
  - `shared/schemas/event_envelope.json`
  - `shared/types/contracts.ts`
  - `app/src/types/contracts.ts`
  - `sidecar/models/contracts.py`
  - `sidecar/models/__init__.py`
  - `sidecar/main.py`
  - `README.md`

### 3. How to Run and Test
- Run sidecar: `python -m uvicorn sidecar.main:app --port 8000`
- Connect via WebSocket and send a test `user_message` or `approval_response` JSON envelope.
- Observe immediate Queen acknowledgement or updated whiteboard card broadcast.

### 4. Assumptions Made
- In mock mode, an `approval_response` with `decision: "approve"` marks the card as `done`, whereas `decision: "redirect"` marks the card as `failed` with optional notes preserved.
- When live mode is active (`SWARM_MODE=live`), incoming client messages are routed to the registered `RunManager`.

### 5. What Is Not Done
- Real LLM completions via provider fallback chain (scheduled for Stage 2).
- Agent execution loop with Queen, Workers and Scribe (scheduled for Stage 3).
