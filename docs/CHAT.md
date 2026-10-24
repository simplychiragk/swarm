# Swarm Real-Time Agent Chat Architecture

This document describes Swarm's in-process concurrent agent messaging system, channel taxonomy, thread lifecycle, and decision board integration.

---

## 1. Concurrency Model

- Agents in Swarm (`queen`, `scribe`, `fe_worker`, `be_worker`, `research_bee`, `qa_bee`) operate as concurrent `asyncio` tasks.
- Each agent has an isolated FIFO inbox queue (`asyncio.Queue`).
- Communication is routed through the central in-process `MessageBus` (`sidecar/agents/bus.py`).
- All messages are:
  1. Appended to the per-run append-only SQLite log (`events` table).
  2. Broadcasted live to Tauri / React frontend clients over WebSocket (`ws://127.0.0.1:8000/ws`).
  3. Routed to relevant agent inboxes according to channel membership, direct addresses (`to`), or mentions (`mentions`).

---

## 2. Channel Layout

| Channel | Purpose | Members | Frequency |
|---|---|---|---|
| `hive` | Swarm-wide high-level updates, goal decomposition, milestone announcements, human approval gates. | Queen, Scribe, FE Worker, BE Worker, Research Bee, QA Bee | Moderate |
| `plan` | Requirement refinement, architecture alignment, interview clarifications, work breakdowns. | Queen, Scribe, FE Worker, BE Worker | Early burst |
| `build` | High-frequency technical exchange: API schemas, prop types, state models, code diffs, integration handoffs. | FE Worker, BE Worker, Scribe | High |
| `qa` | Live testing, browser action validation, screenshot evidence, bug reports, fix verification loops. | QA Bee, FE Worker, BE Worker, Scribe | Late burst |

Agents only receive messages belonging to channels they subscribe to, preventing context window saturation.

---

## 3. Intent Taxonomy

Every `FeedMessage` carries a semantic `intent` indicating its functional purpose:

| Intent | Description | Behavior |
|---|---|---|
| `chat` | General peer discussion or informational update. | Standard broadcast & inbox routing. |
| `proposal` | An agent proposes an architectural, API, or design choice. | Encourages peer review and critique. |
| `critique` | Constructive feedback on an active proposal or implementation. | Stays inside the relevant thread. |
| `decision` | **Agreed architectural choice or contract.** | **Automatically creates a Honeycomb Whiteboard Card (`card_upsert`) and records to the SQLite `decisions` table.** |
| `handoff` | Transferring responsibility or output to another worker. | Explicitly alerts recipient worker inbox. |
| `blocked` | An agent encounters a blocker or policy barrier. | Elevates to Queen and emits warning alert. |

---

## 4. Thread Lifecycle & Auto-Summarization

1. **Thread Attribution**: Related messages carry a shared `thread_id` (e.g. `thread-waitlist-api`).
2. **Turn Tracking**: The `MessageBus` increments turn counters for each active `thread_id`.
3. **Auto-Summarization**:
   - When a thread reaches the configured threshold (default: `8` turns), the bus invokes auto-summarization.
   - Scribe generates a synthesized recap of the discussion.
   - Scribe records the thread as `summarized` in the SQLite `threads` table.
   - A summary status message is broadcasted to keep channels readable and uncluttered.

---

## 5. Live Presence & Token Streaming

- **`agent_status`**: Emitted whenever an agent changes operational phase:
  - `idle`: Awaiting incoming tasks.
  - `thinking`: Prompting LLM or planning next step.
  - `working`: Generating code or calling permission-gated tools.
  - `blocked`: Awaiting human approval or peer dependency.
- **`feed_chunk`**: Emitted for token-by-token streaming of long explanations or code blocks, providing real-time visual feedback in the UI before full message completion.
