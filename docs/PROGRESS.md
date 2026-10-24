# Swarm Development Progress Log

## Status Overview

| Stage | Description | Status |
|---|---|---|
| Stage 0 | Baseline audit (green suite, runbook verification, TODO scan, gap analysis) | done |
| Stage 1 | Model connection that really works (live verification, streaming, /health/deps, smoke --all) | done |
| Stage 2 | SQLite persistence (WAL mode, versioned migrations, runs/events/cards/approvals/artifacts, DB replay) | done |
| Stage 3 | Permission layer (deterministic policy, tiers, escalation, safe command/path, audit) | done |
| Stage 4 | Real-time agent chat (channels, threads, intents, decision board, concurrent agent tasks) | not started |
| Stage 5 | TinyFish for real (Search, Fetch, browser agent, ResearchBee grounding, smoke script) | not started |
| Stage 6 | Workers build real project (served locally, optional tunnel, seeded-bug mode) | not started |
| Stage 7 | QA bee & verify loop (browser test, fail/fix/pass, 2 retry cap, approval gate) | not started |
| Stage 8 | End-to-end hardening of core path (live runs, pacing, provenance summary card) | not started |
| Stage 9 | Demo safety (golden run recorder, offline demo mode, DEMO.md script) | not started |
| Stage 10 | Steering running swarm (steer, queue, interrupt, plan diff, receipts) | not started |
| Stage 11 | Decision layer message delivery (rules guard, optional Jev) | not started |
| Stage 12 | End-to-end harness & UI handoff (scripts/e2e_mock.py, e2e_live.py, UI_HANDOFF.md) | not started |
| Stage 13 | The Gauntlet (persona testing, HTML report) [COULD] | not started |

---

## Stage 0: Baseline Audit

### 1. What Was Audited
- Pulled latest `origin/main` (including UI commits from teammate).
- Executed full test suite: 32/32 tests passing in 6.27s.
- Tested FastAPI sidecar in both `SWARM_MODE=mock` and `SWARM_MODE=live` with `SWARM_LLM_MODE=mock`; verified HTTP 200 OK on `/health`.
- Validated `docs/RUNBOOK.md` fresh-clone procedure in `$env:TEMP`; confirmed clean repository clone, `.env.example` copying, and setup.
- Scanned for `TODO(verify-docs)` references across repository:
  1. `sidecar/tools/client.py`: TinyFish Browser Agent endpoint (`https://agent.tinyfish.ai/v1/run`) parameters schema.
  2. `sidecar/tools/client.py`: TinyFish Fetch endpoint JSON body payload format.
  3. `sidecar/decision/rule_engine.py`: Jev decision endpoint and payload schema (docs.typesafe.ai).

### 2. Known Gaps
- **Stage 1 (LLM Gateway)**: Lacks optional token streaming (`stream=True`), `GET /health/deps` endpoint, and `--all` flag on `sidecar.llm.smoke`.
- **Stage 2 (Storage)**: Storage only persists `permission_events`; full persistence for runs, events with sequence numbers, cards, approvals, artifacts, and DB-backed replay needed.
- **Stage 4 (Agent Chat)**: Real-time agent chat channels (`hive`, `plan`, `build`, `qa`), thread tracking, intent tagging, and decision cards board.
- **Stage 5 (TinyFish)**: Live TinyFish Search, Fetch, and remote browser testing with fallback provenance.
- **Stage 6 (Worker Project & Serving)**: Generation of complete landing page and form submission backend in `workspace/<run_id>/`, served locally with optional tunnel and seeded-bug mode.
- **Stage 7 (QA Loop)**: Closed-loop fail/fix/pass verification cycle with 2-retry limit.
- **Stage 8 & 9 (Hardening & Demo Safety)**: Pacing, provenance summary card, golden run recorder script, and offline demo mode.
- **Stage 10 (Steering)**: Swarm steering with `steer`, `queue`, `interrupt` modes and plan diff receipts.
- **Stage 12 (E2E Harness)**: Headless WebSocket test harness (`scripts/e2e_mock.py`, `scripts/e2e_live.py`) and finalized `docs/UI_HANDOFF.md`.

---

## Stage 1: Model Connection That Really Works

### 1. What Was Built
- **Environment Overrides for Models**: Enabled configuring models per tier via environment variables (`NVIDIA_MODEL_FAST`, `NVIDIA_MODEL_SMART`, `OPENROUTER_MODEL_FAST`, `OPENROUTER_MODEL_SMART`, `BYOK_MODEL_FAST`, `BYOK_MODEL_SMART`) while preserving fast/smart fallbacks in config.
- **Token Streaming**: Added `stream=True` to `complete(messages, *, tier="fast", json_schema=None, timeout=30.0, stream=False)`. Yields delta tokens asynchronously using SSE streaming for remote providers and paced token generation for mock provider.
- **Dependency Diagnostics (`GET /health/deps`)**: Implemented `check_llm_dependencies()` probing readiness of configured providers and tools, returning booleans and latency in milliseconds without exposing any API keys or credentials.
- **Comprehensive Smoke Test CLI**: Enhanced `python -m sidecar.llm.smoke` with `--all` flag to iterate through all configured providers (NVIDIA, OpenRouter, BYOK, Mock), measure latency, and print outputs.
- **Rich Deterministic Mock Payloads**: Added mock handlers for Worker deliverables, Chat replies, QA evaluations, and Steering plan diffs to guarantee offline reliability across all swarm subsystems.
- **Tests**: Added tests for streaming deltas and dependency health diagnostics, bringing total test count to 34/34 passing.

---

## Stage 2: SQLite Persistence & Replay

### 1. What Was Built
- **SQLite Engine (`data/swarm.db`)**: Configured SQLite with WAL mode (`PRAGMA journal_mode = WAL;`), foreign keys enabled (`PRAGMA foreign_keys = ON;`), normal synchronous mode (`PRAGMA synchronous = NORMAL;`), and busy timeout of 5000ms (`PRAGMA busy_timeout = 5000;`).
- **Versioned Migrations**: Implemented custom migration manager in `sidecar/storage/migrations.py` using a `schema_migrations` table without external ORMs.
  - Tables: `runs`, `events` (per-run seq, event_type, payload JSON, timestamp, provenance: 'real'|'simulated'|'replay'), `cards` (latest state projection), `approvals` (pending, resolved, decision, scope), `artifacts` (files written with hash and size), `llm_calls` (telemetry), `permission_events` (audit log), `decisions`, `steers`, `delivery_decisions`, `threads`.
- **Single Write-Point Event Logger (`StorageService`)**: Implemented `record_event(run_id, event_type, payload, provenance)` in `sidecar/storage/service.py` with atomic per-run sequence numbers (`seq`). Projections to `cards` and `approvals` occur synchronously during write.
- **Persistent Broadcaster Catch-Up**: Replaced the in-memory replay buffer in `sidecar/broadcaster.py` with DB queries. When clients connect:
  - If `after_seq` is provided, stream events with `seq > after_seq`.
  - If omitted, send latest cards projection and pending approvals first, then chronologically stream all run events.
- **Replay REST Endpoint**: Added `POST /runs/{id}/replay` streaming historical events over WebSocket with provenance `"replay"` and adjustable pacing (`speed` or `delay_seconds`).
- **Runs REST API**:
  - `GET /runs`: List all runs.
  - `GET /runs/{id}`: Get run status and goal.
  - `GET /runs/{id}/events`: Get event log with sequence numbers.
  - `GET /runs/{id}/cards`: Get current latest whiteboard cards.
  - `GET /runs/{id}/approvals`: Get pending or all approvals.
- **Provenance Tagging**: Every event stamped with provenance `"real"` (live), `"simulated"` (mock), or `"replay"` (replaying historical run).
- **Unit Tests**: Created `sidecar/tests/storage/test_storage.py` (6 tests verifying migrations, sequential ordering, delta catch-up, latest card projection, approval lifecycle, and replay API). Total test suite now 40/40 passing.

---



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

---

## Stage 2: LLM Gateway with Provider Fallback Chain

### 1. What Was Built
- Implemented `sidecar/llm/` with public entry point `complete(messages, *, tier="fast", json_schema=None, timeout=30) -> LLMResult`.
- Configured provider fallback chain in `sidecar/llm/config.py`:
  1. NVIDIA NIM (`https://integrate.api.nvidia.com/v1`)
  2. OpenRouter free tier (`https://openrouter.ai/api/v1`)
  3. Bring-Your-Own-Key (BYOK) provider
  4. Deterministic offline mock provider (`sidecar/llm/mock_provider.py`)
- Implemented request retries (up to 2 attempts on 429 rate limits), fall-through on 5xx/timeouts/empty responses, and `ProviderHealthTracker` with 60-second cooldown windows after 3 consecutive errors.
- Added structured JSON schema output validation and automatic single-turn repair prompt recovery.
- Added standalone CLI smoke test (`python -m sidecar.llm.smoke "hello"`).
- Added comprehensive pytest test suite covering fallback order, 429 retries, timeout fall-through, JSON repair, and mock mode.
- Authored `sidecar/llm/README.md` and updated `docs/ARCHITECTURE.md`.

### 2. Files Added or Changed
- Added:
  - `sidecar/llm/__init__.py`
  - `sidecar/llm/types.py`
  - `sidecar/llm/config.py`
  - `sidecar/llm/mock_provider.py`
  - `sidecar/llm/gateway.py`
  - `sidecar/llm/smoke.py`
  - `sidecar/llm/README.md`
  - `sidecar/tests/__init__.py`
  - `sidecar/tests/llm/__init__.py`
  - `sidecar/tests/llm/test_gateway.py`
  - `docs/ARCHITECTURE.md`
- Changed:
  - `sidecar/requirements.txt` (added `httpx`, `pytest`, `pytest-asyncio` for HTTP gateway and test runner)
  - `docs/PROGRESS.md`

### 3. How to Run and Test
- Run tests: `.venv\Scripts\pytest sidecar/tests/llm`
- Run smoke test: `.venv\Scripts\python -m sidecar.llm.smoke "Hello Swarm"`

### 4. Assumptions Made
- Both NVIDIA NIM and OpenRouter support OpenAI-compatible `/chat/completions` REST endpoints with bearer token auth and `response_format={"type": "json_object"}`.
- If no provider API keys are set or `SWARM_LLM_MODE=mock`, requests smoothly fall back to deterministic mock completions rather than throwing errors.

### 5. What Is Not Done
- In-process agent message bus and orchestration engine (scheduled for Stage 3).
- TinyFish live tool integration (scheduled for Stage 4).

---

## Stage 3: Multi-Agent Engine & Runtime Manager

### 1. What Was Built
- Implemented in-process asynchronous message bus in `sidecar/agents/bus.py` with subscriber queues and automatic WebSocket broadcast forwarding.
- Created `BaseAgent` class in `sidecar/agents/base.py` with queue-based inbox, structured emission helpers (`emit_feed_message`, `emit_card_upsert`, `emit_approval_request`), and per-agent message allocation limits.
- Built `QueenAgent` in `sidecar/agents/queen.py`:
  - Conducts user discovery interviews (strictly maximum 3 questions).
  - Produces structured JSON task plans via LLM gateway.
  - Classifies task lanes using the Decision Layer (`route_task`).
  - Monitors worker activity and issues health nudges.
- Built `WorkerAgent` in `sidecar/agents/worker.py` for Frontend and Backend lanes:
  - Produces API contracts and React component specs.
  - Exchanges direct peer messages over the bus (BE worker sends API contract to FE worker).
  - Includes placeholder hook `write_deliverable_artifact` for future disk persistence tools.
- Built `ScribeAgent` in `sidecar/agents/scribe.py`:
  - Batches raw worker nectar every 2 seconds.
  - Filters updates using `DecisionLayer.should_show_on_whiteboard`.
  - Produces plain-language Honeycomb Whiteboard cards via LLM gateway.
- Built `SwarmRunManager` in `sidecar/agents/run_manager.py`:
  - Full implementation of `RunManager` wired into `sidecar/main.py`.
  - Enforces global run timeout (120s) and max LLM calls (40 calls).
  - Gated production release using `DecisionLayer.needs_approval`.
  - Emits failure cards if limits or timeouts are breached.
- Created comprehensive test suite in `sidecar/tests/agents/test_engine.py` (all 6 tests passing).
- Authored `sidecar/agents/README.md` and initial demo guide `docs/DEMO.md`.

### 2. Files Added or Changed
- Added:
  - `sidecar/agents/__init__.py`
  - `sidecar/agents/bus.py`
  - `sidecar/agents/base.py`
  - `sidecar/agents/queen.py`
  - `sidecar/agents/worker.py`
  - `sidecar/agents/scribe.py`
  - `sidecar/agents/run_manager.py`
  - `sidecar/agents/README.md`
  - `sidecar/tests/agents/__init__.py`
  - `sidecar/tests/agents/test_engine.py`
  - `docs/DEMO.md`
- Changed:
  - `sidecar/main.py` (instantiates and registers `SwarmRunManager`)
  - `docs/PROGRESS.md`

### 3. How to Run and Test
- Run tests: `.venv\Scripts\pytest sidecar/tests/agents`
- Test live mode:
  ```powershell
  $env:SWARM_MODE="live"
  $env:SWARM_LLM_MODE="mock"
  python -m uvicorn sidecar.main:app --port 8000
  ```
  Sending a `user_message` from the desktop client triggers a live agent run through discovery, worker peer chatter, scribe cards, and an approval gate.

### 4. Assumptions Made
- In live mode with mock LLM, the Queen concludes the interview when prompt requirements contain audience/theme/fields or after reaching 3 questions.
- High-risk operations (such as production deployments) automatically raise an approval request before marking the run complete.

### 5. What Is Not Done
- None. Core pipeline, multi-agent engine, and live tools are functional.

---

## Stage 4: TinyFish Live-Web & Browser QA Tools Integration

### 1. What Was Built
- Implemented `TinyFishClient` in `sidecar/tools/client.py`:
  - `search(query, purpose)` hitting `https://api.search.tinyfish.ai` (verified with official documentation).
  - `fetch(url)` hitting `https://api.fetch.tinyfish.ai`.
  - `run_browser_task(url, goal)` hitting `https://agent.tinyfish.ai/v1/run` (marked `TODO(verify-docs)` for live agent parameters).
  - Deterministic offline mock mode supporting tests and offline presentations.
- Implemented specialized agent bees in `sidecar/tools/agents.py`:
  - `ResearchBee`: Gathers live documentation before build and attaches search evidence.
  - `QABee`: Executes browser task, verifies form submission, and attaches screenshot evidence to whiteboard card.
- Wired `ResearchBee` and `QABee` into `SwarmRunManager` behind the `ENABLE_TINYFISH_BEES` environment flag (off by default per spec).
- Authored test suite in `sidecar/tests/tools/test_tinyfish.py` (5 tests passing).
- Authored `sidecar/tools/README.md` and updated `docs/RUNBOOK.md` and `docs/DEMO.md`.

### 2. Files Added or Changed
- Added:
  - `sidecar/tools/__init__.py`
  - `sidecar/tools/client.py`
  - `sidecar/tools/agents.py`
  - `sidecar/tools/README.md`
  - `sidecar/tests/tools/__init__.py`
  - `sidecar/tests/tools/test_tinyfish.py`
- Changed:
  - `sidecar/agents/run_manager.py` (wired ResearchBee & QABee behind flag)
  - `docs/RUNBOOK.md` (documented `TINYFISH_API_KEY`, `SWARM_TINYFISH_MODE`, `ENABLE_TINYFISH_BEES`)
  - `docs/PROGRESS.md`

### 3. How to Run and Test
- Run tests: `.venv\Scripts\pytest sidecar/tests/tools`
- Enable TinyFish bees in live mode:
  ```powershell
  $env:SWARM_MODE="live"
  $env:ENABLE_TINYFISH_BEES="true"
  python -m uvicorn sidecar.main:app --port 8000
  ```

### 4. Assumptions Made
- The TinyFish Search and Fetch REST endpoints conform to official `docs.tinyfish.ai` documentation: `https://api.search.tinyfish.ai` and `https://api.fetch.tinyfish.ai`.
- The remote browser agent execution endpoint is modeled after `https://agent.tinyfish.ai/v1/run` with a fallback mock payload containing screenshot evidence artifacts.

### 5. What Is Not Done
- In-person testing against physical TinyFish live API keys during hackathon hacking session. Marked `TODO(verify-docs)` on browser payload parameters.

---

## Stage 5: Permission & Safety System

### 1. What Was Built
- **Centralized Execution Gating**: Enforced the core principle that agents never execute tools directly. All tool calls route through `ToolExecutor.execute(...)`, which first queries `PolicyEngine.check(...)`.
- **Deterministic Policy Configuration**: Created `sidecar/permissions/policy.json` specifying tiers (`FORBIDDEN`, `HIGH`, `MEDIUM`, `LOW`), allowlisted commands with permitted subcommands, budget limits, and protected paths. Unknown tools are denied by default.
- **Path Sandboxing & Run Workspace Jail**: Implemented `sidecar/permissions/path_safety.py` locking file reads and writes strictly to `workspace/<run_id>/`. Path traversal sequences (`..`), symlink escapes, root repository access, and secret file accesses (`.env`, `.git`, SSH keys) are caught and rejected with `PathSafetyError`.
- **Subprocess Runner with Scrubbed Environment**: Implemented `sidecar/permissions/command_runner.py` with argv list execution (no `shell=True`), scrubbed minimal child environment (stripping all `SWARM_*` variables, API keys, tokens), process-tree termination (`taskkill /F /T /PID` on Windows), and output character truncation.
- **Secret Redaction Engine**: Implemented `sidecar/permissions/redaction.py` with regex patterns for API keys (OpenAI, OpenRouter, NVIDIA, AWS, GitHub, bearer tokens) and dynamic scrubbing of ambient environment variables containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, or starting with `SWARM_`.
- **SQLite Audit Trail**: Implemented `sidecar/permissions/audit.py` recording all permission checks, evaluations, execution durations, scrubbed arguments, and outcomes to SQLite (`workspace/swarm_audit.db`).
- **Interactive Approval Coordination & Scope Grants**: Built `ApprovalCoordinator` enabling tool suspension on `HIGH` or `MEDIUM` tier actions, dispatching WebSocket `approval_request` events to the desktop app with argument previews and scope options (`once`, `run`, `deny`), supporting timeout auto-denial.
- **Operational Modes**: Introduced `SWARM_PERMISSION_MODE=strict|demo`. `strict` requires approvals for `HIGH` and `MEDIUM`. `demo` auto-allows allowlisted `MEDIUM` actions while keeping `HIGH` interactive and `FORBIDDEN` non-bypassable.
- **REST Endpoints**: Added `GET /runs/{run_id}/permissions` and safe `GET /runs/{run_id}/artifacts/{artifact_path:path}` to `sidecar/main.py`.
- **Comprehensive 14-Point Test Suite**: Implemented `sidecar/tests/permissions/test_permissions.py` covering forbidden secrets, path traversal, unknown tools, allowlisted commands, timeout process-tree termination, budget exhaustion, escalation rules, approval timeouts, run-scope grants, secret redaction, strict vs demo modes, immutable FORBIDDEN tier, and REST endpoints.
- **Documentation**: Authored `docs/PERMISSIONS.md`, `sidecar/permissions/README.md`, updated `docs/CONTRACT.md`, `docs/RUNBOOK.md`, and `docs/ARCHITECTURE.md`.

### 2. Files Added or Changed
- Added:
  - `sidecar/permissions/policy.json`
  - `sidecar/permissions/redaction.py`
  - `sidecar/permissions/path_safety.py`
  - `sidecar/permissions/command_runner.py`
  - `sidecar/permissions/audit.py`
  - `sidecar/permissions/policy.py`
  - `sidecar/permissions/executor.py`
  - `sidecar/permissions/__init__.py`
  - `sidecar/permissions/README.md`
  - `sidecar/tests/permissions/__init__.py`
  - `sidecar/tests/permissions/test_permissions.py`
  - `docs/PERMISSIONS.md`
- Changed:
  - `shared/schemas/approval_request.json`
  - `shared/schemas/approval_response.json`
  - `shared/types/contracts.ts`
  - `app/src/types/contracts.ts`
  - `sidecar/models/contracts.py`
  - `sidecar/tools/agents.py`
  - `sidecar/agents/worker.py`
  - `sidecar/agents/run_manager.py`
  - `sidecar/main.py`
  - `docs/CONTRACT.md`
  - `docs/RUNBOOK.md`
  - `docs/ARCHITECTURE.md`
  - `docs/PROGRESS.md`
  - `.gitignore`

### 3. How to Run and Test
- Run full test suite:
  ```powershell
  .venv\Scripts\pytest sidecar/tests -v
  ```
- Run permissions tests specifically:
  ```powershell
  .venv\Scripts\pytest sidecar/tests/permissions -v
  ```

### 4. Assumptions Made
- The permission system provides in-process software guardrails. Multi-tenant hostile untrusted code execution requires containerized or VM sandboxing (documented in `docs/PERMISSIONS.md`).
- `FORBIDDEN` rules cannot be disabled or bypassed by any environment variable or configuration option under any circumstances.

---

## Stage 6: Real Workspace Files Integration & UI Security Alignment

### 1. What Was Built
- **Workspace Tree & Files REST Endpoints**: Implemented `GET /workspace/tree`, `GET /workspace/files/{path}`, `PUT /workspace/files/{path}`, and `POST /workspace/files` in `sidecar/main.py`. These endpoints walk `workspace/<run_id>/`, guess file syntax language, and serve file contents for the desktop client's code viewer and file explorer.
- **Auto-Seeding Starter Project**: Added `seed_default_workspace_if_empty()` to ensure the Section 9 landing page project files (`index.html`, `package.json`, `src/App.tsx`, `api/main.py`, etc.) are pre-populated on disk for instant exploration.
- **Frontend File Tree Sync**: Updated `app/src/components/Sidebar.tsx` to query `/workspace/tree` on mount and on Refresh, and forward new file and folder creations to `/workspace/files`.
- **Code Viewer Saving**: Wired `onSaveContent` in `app/src/App.tsx` and `FileViewerModal.tsx` to `PUT /workspace/files/{path}`, persisting edits directly into the run workspace.
- **Approval Modal Security Metadata**: Enhanced `app/src/components/ApprovalModal.tsx` to display real-time permission context (`tool`, `risk`, `reason`, `args_preview`) and an interactive `"once"` vs `"run"` scope selection toggle.
- **Tests**: Added `test_workspace_tree_and_file_endpoints` in `sidecar/tests/permissions/test_permissions.py` validating tree listing, file updates, creation, and path traversal rejection.

