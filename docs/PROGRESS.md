# Swarm Development Progress Log

## Status Overview

| Stage | Description | Status |
|---|---|---|
| Stage 0 | Baseline audit (green suite, runbook verification, TODO scan, gap analysis) | done |
| Stage 1 | Model connection that really works (live verification, streaming, /health/deps, smoke --all) | done |
| Stage 2 | SQLite persistence (WAL mode, versioned migrations, runs/events/cards/approvals/artifacts, DB replay) | done |
| Stage 3 | Permission layer (deterministic policy, tiers, escalation, safe command/path, audit) | done |
| Stage 4 | Real-time agent chat (channels, threads, intents, decision board, concurrent agent tasks) | done |
| Stage 5 | TinyFish for real (Search, Fetch, browser agent, ResearchBee grounding, smoke script) | done |
| Stage 6 | Workers build real project (served locally, optional tunnel, seeded-bug mode) | done |
| Stage 7 | QA bee & verify loop (browser test, fail/fix/pass, 2 retry cap, approval gate) | done |
| Stage 8 | End-to-end hardening of core path (live runs, pacing, provenance summary card) | done |
| Stage 9 | Demo safety (golden run recorder, offline demo mode, DEMO.md script) | done |
| Stage 10 | Steering running swarm (steer, queue, interrupt, plan diff, receipts) | done |
| Stage 11 | Decision layer message delivery (rules guard, optional Jev) | done |
| Stage 12 | End-to-end harness & UI handoff (scripts/e2e_mock.py, e2e_live.py, UI_HANDOFF.md) | done |
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

## Stage 4: Real-Time Agent Chat That Feels Alive

### 1. What Was Built
- **Concurrent Agent Tasks & Inboxes**: Configured agents to operate as concurrent `asyncio` tasks with isolated FIFO queues (`asyncio.Queue`) registered directly on the `MessageBus` (`sidecar/agents/bus.py`).
- **Channel Partitioning (`hive`, `plan`, `build`, `qa`)**:
  - `hive`: Swarm-wide high-level updates, goal announcements, status reports, approval gates.
  - `plan`: Architecture and planning room (Queen, Scribe, FE Worker, BE Worker).
  - `build`: High-frequency technical code, API schemas, and component interfaces (FE Worker, BE Worker, Scribe).
  - `qa`: Verification room, browser testing results, bug logs, and fix verification (QA Bee, FE Worker, BE Worker, Scribe).
- **Direct Messaging & Mentions**: Supported explicit peer targeting via `to="agent_name"` and `@mentions` parsing, automatically delivering to target agent inboxes without spamming unrelated agents.
- **Thread Lifecycle & Auto-Summarization**:
  - Turn counting per `thread_id`.
  - Threshold-based auto-summarization (default: 8 turns).
  - Auto-generated thread summary posted by Scribe to the channel and recorded in the SQLite `threads` table.
- **Decisions Board**:
  - Messages with `intent="decision"` are automatically extracted and recorded into the `decisions` table.
  - Scribe immediately creates and broadcasts a Honeycomb Whiteboard Card (`card_upsert`) with `status="done"`, documenting the agreed contract and stakeholders.
- **Presence & Streaming Tokens**:
  - `agent_status` event (`idle`, `thinking`, `working`, `blocked`) for real-time typing/working indicators in the UI.
  - `feed_chunk` event for streaming delta tokens of long agent thoughts or code generations.
- **Contract Type Mirror**: Updated `sidecar/models/contracts.py`, `shared/types/contracts.ts`, and mirrored to `app/src/types/contracts.ts`.
- **Documentation**: Authored `docs/CHAT.md` detailing channel routing, intent semantics, and thread lifecycle.
- **Unit Tests**: Added `sidecar/tests/agents/test_chat.py` (6 tests covering channel isolation, direct messaging, threading, turn tracking, auto-summarization, decision board, and presence/chunk events). Suite now 46/46 passing.

---

## Stage 5: TinyFish Integration for Real

### 1. What Was Built
- **TinyFish API Client (`sidecar/tools/client.py`)**:
  - Search: POST `/v1/search` (`query`, `limit`, `purpose`) with fallback to `https://api.search.tinyfish.ai`. Verified live in smoke test.
  - Fetch: POST `/v1/fetch` (`url`) extracting clean markdown and text, with fallback to `https://api.fetch.tinyfish.ai`.
  - Browser Agent: POST `/v1/run` (`url`, `goal`, `options`) with polling `GET /v1/run/{id}` returning `{status, verdict, details, evidence}`.
  - Resolved `TODO(verify-docs)` comments with robust schemas and fast timeouts (5s for discovery, 10s for browser).
- **Honest Provenance Tagging**:
  - If `TINYFISH_API_KEY` is present and live call succeeds: stamped with `provenance: "real"`.
  - If keys are missing, network fails, or mock mode is requested: seamlessly falls back to realistic deterministic data with `provenance: "simulated"`.
- **ResearchBee Plan Grounding**:
  - Queries TinyFish Search for `"best practice waitlist form fields 2026"`, fetches top result content, and posts a nectar card to the Honeycomb Whiteboard.
  - Directly posts an `intent="proposal"` message to channel `plan` grounding the Queen, FE Worker, and BE Worker on minimal 3-field forms (Name, Work Email, Role) and instant queue confirmation toasts.
- **QABee End-to-End Browser Testing**:
  - Dispatches TinyFish browser agent to target page with verification goals.
  - Generates structured evaluation (`PASS` or `FAIL`), captures screenshot evidence, and posts result card to whiteboard.
- **Smoke Script (`scripts/smoke_tinyfish.py`)**:
  - Automated smoke test executing Search, Fetch, and Browser Agent against `example.com` or live API.
  - Measures execution latency per step and writes full audit evidence to `data/qa_smoke.json`.
- **Unit Tests**: Updated `sidecar/tests/tools/test_tinyfish.py` with 6 unit tests covering mock fallbacks, evidence cards, and plan grounding proposals. Full test suite now 47/47 passing.

---

## Stage 6: Workers Build Real Project, Serving & Seeded-Bug Demo Mode

### 1. What Was Built
- **Real Workspace Files Generated in `workspace/<run_id>/`**:
  - `index.html`: Fully semantic HTML5 landing page with hero, waitlist form (name, email, role dropdown, submit button), and toast notification.
  - `style.css`: Clean dark honeycomb theme adhering to 8px grid, CSS variables, and accessibility (`prefers-reduced-motion`).
  - `app.js`: Client-side submit listener validating inputs, submitting via `fetch()` to `/api/waitlist`, and rendering confirmation banner with assigned queue number `#42`.
  - `api/main.py`: Real FastAPI waitlist submission endpoint with Pydantic email validation.
- **Sidecar Preview Serving (`GET /runs/{run_id}/preview/`)**:
  - Direct local HTTP preview endpoint serving HTML, CSS, JS, and image assets securely using `resolve_safe_path`.
  - Dedicated waitlist submission handler at `POST /runs/{run_id}/api/waitlist` and `POST /api/waitlist` returning 201 Created and queue position.
- **Public Tunnel Support**:
  - Added operational runbook guide for `localtunnel`, `cloudflared`, and `ngrok` so cloud-based TinyFish browser agents can inspect local previews.
  - Configurable via `SWARM_PREVIEW_URL`.
- **Seeded-Bug Demo Mode (`SWARM_DEMO_MODE=seeded_bug`)**:
  - FE Worker deliberately introduces a disabled submit button into `index.html` on initial build.
  - When fix task is received from Queen, `fe_worker.apply_fix()` rewrites the file, enabling the button and restoring form handlers.
- **Unit Tests**: Added `sidecar/tests/agents/test_worker_build.py` (3 tests verifying real file generation, preview serving, waitlist submission API, and seeded bug introduction).

---

## Stage 7: QA Bee Automated Verification Loop & Failure Routing

### 1. What Was Built
- **QABee Browser Verification Loop**:
  - Dispatches TinyFish browser agent against preview URL (`/runs/{run_id}/preview/` or tunnel).
  - Evaluates form inputs, submission response, and toast banner visibility.
  - Captures screenshot and browser log evidence, posting cards to the Honeycomb Whiteboard.
- **Queen Failure Routing (`route_qa_failure`)**:
  - When QA reports `FAIL`, Queen analyzes failure details (404/route -> BE Worker; button/disabled/form -> FE Worker).
  - Emits targeted fix assignment to responsible worker in channel `qa`.
  - Cap of 2 retries: if failures exceed 2 retries, Queen halts and emits an emergency `card-qa-emergency` gate with status `needs_approval`.
- **Worker Auto-Fix Loop (`apply_fix`)**:
  - Targeted worker applies corrections in `workspace/<run_id>/` and reports readiness for retest in channel `qa`.
- **Full Fail -> Fix -> Pass Verification**:
  - Tested end-to-end with seeded-bug mode: initial run fails, Queen delegates fix to FE worker, worker re-generates enabled button, retest passes with `verdict: PASS`!
- **Unit Tests**: Added `sidecar/tests/agents/test_qa_loop.py` (3 tests covering clean pass, complete fail->fix->pass loop, and retry limit emergency gate). Total suite now 53/53 passing.

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

## Stage 8: End-to-End Hardening of Core Path & Provenance Summary Card

### 1. What Was Built
- **Pacing Engine (`get_pacing_delay`)**: Implemented configurable execution pacing controlled via `SWARM_PACING=real|fast|instant`. Real pacing spaces out agent messages and phases for realistic live presentation; fast/instant modes accelerate test executions and CI.
- **Tool Execution Telemetry & Latency Tracking**: Added in-memory tracking in `ToolExecutor` logging tool invocations, execution duration (`latency_ms`), tier, outcome, and provenance (`real` vs `simulated`) per run.
- **Run Provenance & Verification Audit Card**: Emitted `card-provenance-summary` on the whiteboard and status feed message prior to the human approval gate. Transparently documents every tool call, its execution latency, and its live provenance so judges can verify live network operations at a glance.
- **Unit & Integration Tests**: Verified `test_end_to_end_run_to_approval` passes with the provenance audit card emitted. Entire test suite (53/53 tests) green.


---

## Stage 6: Real Workspace Files Integration & UI Security Alignment

### 1. What Was Built
- **Workspace Tree & Files REST Endpoints**: Implemented `GET /workspace/tree`, `GET /workspace/files/{path}`, `PUT /workspace/files/{path}`, and `POST /workspace/files` in `sidecar/main.py`. These endpoints walk `workspace/<run_id>/`, guess file syntax language, and serve file contents for the desktop client's code viewer and file explorer.
- **Auto-Seeding Starter Project**: Added `seed_default_workspace_if_empty()` to ensure the Section 9 landing page project files (`index.html`, `package.json`, `src/App.tsx`, `api/main.py`, etc.) are pre-populated on disk for instant exploration.
- **Frontend File Tree Sync**: Updated `app/src/components/Sidebar.tsx` to query `/workspace/tree` on mount and on Refresh, and forward new file and folder creations to `/workspace/files`.
- **Code Viewer Saving**: Wired `onSaveContent` in `app/src/App.tsx` and `FileViewerModal.tsx` to `PUT /workspace/files/{path}`, persisting edits directly into the run workspace.
- **Approval Modal Security Metadata**: Enhanced `app/src/components/ApprovalModal.tsx` to display real-time permission context (`tool`, `risk`, `reason`, `args_preview`) and an interactive `"once"` vs `"run"` scope selection toggle.
- **Tests**: Added `test_workspace_tree_and_file_endpoints` in `sidecar/tests/permissions/test_permissions.py` validating tree listing, file updates, creation, and path traversal rejection.

---

## Stage 9: Demo Safety (Golden Run & Offline Replay Mode)

### 1. What Was Built
- **Golden Run Recorder (`scripts/make_golden_run.py`)**: Script that extracts a verified successful multi-agent execution run from SQLite (or the reference Section 9 scenario), applies secret redaction across all payloads, stamps every event with `provenance: 'replay'`, and serializes to `data/golden_run.json`.
- **Deterministic Offline Replay Mode (`SWARM_DEMO_MODE=golden`)**: Updated `MockRunner` in `sidecar/mock_runner.py` and WebSocket connection logic in `sidecar/main.py`. When enabled, the sidecar streams directly from `data/golden_run.json` with realistic or instant pacing. Zero LLM calls and zero external network calls are made.
- **Presenter Guide & Pitch Script (`docs/DEMO.md`)**: Authored comprehensive 2-minute stage presenter script with word-for-word pitch, input actions, specific screen cues ("Notice the scribe just turned 14 agent messages into three cards", "Watch the QA bee run the real browser"), and bulletproof backup plans for Wi-Fi drops, API 500s, and provider outages.
- **Unit Tests**: Implemented `sidecar/tests/test_golden_replay.py` validating file structure, absence of secrets, and streaming playback with `provenance: 'replay'`. Total test suite now 55/55 passing.

---

## Stage 10: Steering the Running Swarm

### 1. What Was Built
- **Message Input Modes (`UserMessage.mode`)**: Extended the user message contract with `mode: 'steer' | 'queue' | 'interrupt'` (defaulting to `'steer'`). Preserved full backwards compatibility across Python, Shared Types, and Tauri App contract mirrors.
- **Structured Plan Diff Generation & WebSocket Broadcast (`PlanDiff`, `TaskDiffItem`, `PlanDiffEnvelope`)**: Queen dynamically computes structured diffs (`added`, `modified`, `removed` tasks) upon user steering, broadcasts `plan_diff` events, and emits `[EDITED]` Whiteboard cards.
- **Worker Dynamic Code Adaptation**: FE Worker updates `index.html` and `app.js` with steered inputs (e.g., international phone number with country code picker), while BE Worker updates `api/main.py` Pydantic models.
- **SQLite Steering Receipts**: Implemented `record_steer` and `get_run_steers` in `StorageService` saving steer receipts (`id, run_id, message_id, mode, status, prompt, plan_diff_json, targets_json, timestamp`). Added `GET /runs/{run_id}/steers` endpoint to `sidecar/main.py`.
- **Documentation**: Authored `docs/STEERING.md` detailing steering modes, diff schemas, and UI synchronization.
- **Tests**: Implemented `sidecar/tests/agents/test_steering.py` testing `queue`, `interrupt`, and mid-run phone field additions. All 57 tests green.

---

## Stage 11: Decision Layer Message Delivery (Rules Guard & Optional Jev)

### 1. What Was Built
- **Message Delivery Filtering (`decide_delivery`)**: Implemented intelligent message routing across agent inboxes (`deliver`, `drop`, `summarize`) with confidence scores. Prevents message spam by dropping directed messages intended for other peers, filtering raw database/SQL messages from frontend workers, and filtering CSS styling details from backend workers.
- **Optional Jev Model Call with 500ms Fallback**: Structured `_query_jev` with a strict 500ms timeout. If `JEV_API_KEY` is provided and the model endpoint fails or times out, execution seamlessly falls back to deterministic rules. The demo never hangs or crashes.
- **SQLite Delivery Decision Audit (`delivery_decisions` table)**: Persisted every delivery evaluation (`run_id, message_id, receiver, action, confidence, backend, latency_ms, timestamp`).
- **Whiteboard Filtering with Confidence (`should_show_on_whiteboard`)**: Scribe asks the decision layer whether a message warrants card generation; high-confidence milestones and evidence become cards, while low-confidence back-and-forth chatter stays in the nectar feed.
- **Ops Whiteboard Card Integration & REST API**: Computed delivery statistics (`total, delivered, dropped, summarized, avg_confidence`) and attached them as a `decision_engine` evidence entry to the Ops Provenance summary card. Added `GET /runs/{run_id}/decisions/delivery` endpoint.
- **Unit Tests**: Implemented `sidecar/tests/decision/test_delivery.py` (4 tests validating delivery rules, persistence and stats calculation, Jev timeout fallback, and whiteboard filtering confidence). Full test suite now 61/61 passing.

---

## Stage 12: End-to-End Test Harness & UI Handoff

### 1. What Was Built
- **Automated Mock E2E Harness (`scripts/e2e_mock.py`)**: Headless integration runner that spawns sidecar with `SWARM_MODE=mock` on a dynamic port, connects via WebSocket, sends initial prompt, answers interview questions, handles approval gate, asserts event reception, verifies SQLite event persistence and workspace files, and cleanly exits in < 3s (well under the 15s budget).
- **Automated Live E2E Harness (`scripts/e2e_live.py`)**: Headless live runner executing real multi-agent pipeline with real TinyFish API integration, browser QA verification, release gate approval, and asserting `provenance: 'real'` across all persisted events.
- **UI Handoff Specification (`docs/UI_HANDOFF.md`)**: Comprehensive integration guide for the frontend engineer documenting all event types (`feed_message`, `card_upsert`, `approval_request`, `agent_status`, `feed_chunk`, `plan_diff`), steering modes, provenance indicators, whiteboard badges (`[EDITED]`), live preview URLs, and complete REST API table.
- **Git & Secret Scan**: Verified git history and current working tree against all ambient environment variables and API key patterns. Zero leaks found.





