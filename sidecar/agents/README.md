# Swarm Agent Engine (`sidecar/agents`)

Custom in-process multi-agent orchestration engine for Swarm (no heavy agent frameworks).

---

## Agents & Roles

1. **Queen Agent (`queen.py`)**:
   - **Role:** Interviewer, goal synthesizer, task planner, and monitor.
   - **Discovery:** Interviews the user (bounded by a maximum of 3 clarifying questions).
   - **Planning:** Generates structured task breakdowns with lane tags and dependencies.
   - **Watchdog:** Monitors worker activity timestamps and issues nudges if any worker stalls.

2. **Worker Bee Agents (`worker.py`)**:
   - **Frontend Worker (`Lane.FE`):** Designs UI layouts, components, and form validation using React and Tailwind.
   - **Backend Worker (`Lane.BE`):** Implements endpoints and validators (e.g. `POST /api/waitlist`), and broadcasts the API schema over the bus to the Frontend Worker.
   - **Extension Point:** Includes `write_deliverable_artifact` hook for future file generation tools.

3. **Scribe Agent (`scribe.py`)**:
   - **Role:** Whiteboard synthesizer ("honey from nectar").
   - **Operation:** Subscribes to the live message bus, batches messages every ~2 seconds, filters via `DecisionLayer.should_show_on_whiteboard`, and calls the LLM gateway with a card schema to produce plain-language whiteboard card summaries.

---

## Message Bus & Data Flow

- Implemented in `bus.py` via `MessageBus`.
- Agents publish `FeedMessage` objects to the bus.
- Every `FeedMessage` is automatically wrapped in `FeedMessageEnvelope` and broadcast to connected desktop clients over `/ws`.
- Internal subscribers (Queen, Workers, Scribe) receive messages for peer coordination (e.g., BE notifying FE of route signatures).

---

## Safety Limits & Guardrails

Configured in `SwarmRunManager`:
- **Max Messages per Agent:** 25 messages. Exceeding this raises `AgentMessageLimitError`.
- **Global Run Timeout:** 120 seconds default. Exceeding this halts execution and posts a visible failure card.
- **Max LLM Calls:** 40 calls per run.
- **Approval Gate:** High-stakes actions (such as production deployment) are gated by `DecisionLayer.needs_approval`, requiring client `approval_response` to complete.
