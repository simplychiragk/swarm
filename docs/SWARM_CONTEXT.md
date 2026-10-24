# Swarm: project context

Read this first. It is the shared source of truth for teammates and coding agents (opencode, Claude, etc.). If something here conflicts with what you were told elsewhere, flag it instead of guessing.

## 1. What Swarm is

Swarm (formerly "Hive") is a desktop app where a team of AI agents builds a software project while the user watches and steers in real time.

- A **queen agent** interviews the user, turns the answers into a plan, delegates tasks to workers, and monitors them.
- **Worker bee agents** each own a lane (frontend, backend, database, design, test, docs, ops). They message each other live while they work.
- A **scribe agent** reads the live agent conversation and posts plain-language updates to a **honeycomb whiteboard** in the UI.
- Workers use the live web through **TinyFish**: a research bee gathers current docs before building, and a QA bee tests the finished result in a real browser.
- A **decision layer (Jev)** makes fast structured decisions: task routing, approval gating, whiteboard filtering.

One-line pitch: *a team of AI agents that builds with you, in the open.*

## 2. Why we are building it (the problem)

Multi-agent AI coding is powerful but opaque and unverified:
- Developers cannot see what a team of agents is deciding or why.
- Agents build from model memory, which goes stale on APIs, libraries and docs.
- Results are rarely tested on a real running site before being called done.
- Non-technical teammates cannot follow progress.

Swarm's answer: visibility (whiteboard), freshness (live-web research), verification (browser QA with evidence), control (approval gates, queen oversight).

## 3. Event context

- Event: **HackIIITD** (part of Esya '26, IIIT Delhi), 24-hour in-person final on 24-25 Oct 2026. Powered by TinyFish.
- We qualified through a PPT-only round 1.
- **TinyFish API integration is mandatory.** It must be real, visible in the demo, and explainable in one sentence.
- Team size 2 to 4. Our team: Tanmay Sharma, Chirag Kumar, Priyanshu Tiwari.
- Judging criteria for the final are not confirmed here. Assume: working demo, clear idea, real TinyFish usage, feasibility. Update this section when we know more.

## 4. Vocabulary (keep these names consistent in code and UI)

| Term | Meaning |
|---|---|
| Hive / Swarm | the whole system (Swarm is the current name) |
| Queen | interviewer, planner, delegator, monitor |
| Worker bee | agent that owns one lane |
| Scribe | summarizes agent chatter for the user |
| Nectar | raw agent output and messages |
| Honey | the scribe's clean summaries |
| Honeycomb whiteboard | the live UI board showing honey as cards |
| Lane | a worker's area: FE, BE, DB, Design, Test, Docs, Ops |
| Research bee | worker that uses TinyFish Search/Fetch before building |
| QA bee | worker that uses the TinyFish browser agent to test the result |
| Decision layer | Jev, used for routing, approval gating, filtering |

## 5. Architecture

Layers, top to bottom:

1. **Interface:** Tauri v2 desktop app with React. Hosts the honeycomb whiteboard.
2. **Orchestration:** queen, workers and scribe sharing a live message feed. FastAPI sidecar, WebSockets to the UI. Custom agent-farm pattern (no CrewAI).
3. **Decision layer:** Jev. Takes current system state plus typed questions, returns structured choices with confidence.
4. **Web tools:** TinyFish for Search, Fetch and browser agents.
5. **Models:** LLMs for reasoning and generation with a fallback chain across providers.

Data flow: user -> queen (interview) -> plan -> tasks to workers -> worker messages (nectar) on the live feed -> scribe -> honey cards on the whiteboard. QA evidence (pass/fail, screenshots) attaches to whiteboard cards.

## 6. Stack (decided)

- Tauri v2, React + Vite
- Shadcn/ui + Tailwind, Framer Motion, React Bits, tsParticles
- FastAPI sidecar with WebSockets
- Models: free-model chain (NVIDIA NIM with OpenRouter fallbacks); optional BYOK (Anthropic / OpenRouter / NIM keys) in a settings screen, stored in the Tauri secure store
- Bee avatars: new image assets generated for this hackathon (queen, worker, scribe, QA bee, etc.), shared by the team. No code or assets from earlier projects.

## 7. TinyFish integration (mandatory)

Planned usage:
- **Research bee, before build:** Search and Fetch to pull current documentation and references so workers do not rely on stale model knowledge.
- **QA bee, after build:** browser agent opens the running app, runs key flows, returns pass or fail with evidence (screenshots, notes) shown on the whiteboard.
- **Control:** the decision layer chooses which TinyFish calls are worth making and escalates low-confidence results to the queen.

Notes:
- One teammate has used the TinyFish API hands-on before.
- Check the current TinyFish docs for exact endpoints, auth and limits before coding. Do not assume parameter names.
- Do not hard-code API keys. Use environment variables or the secure store.

## 8. Jev (decision layer)

- Jev is a decision model: it reads system state and typed questions and returns structured decisions with probabilities and confidence. It does not generate text.
- Intended jobs: (1) route a task to the right lane, (2) decide if an action needs human approval, (3) decide which messages are worth putting on the whiteboard.
- It is new and its sources are mostly articles. Verify how to call it before building on it.
- **Fallback is required:** if Jev is unavailable or low-confidence, route to the queen or fall back to a simple rule-based or LLM decision. The demo must not depend on Jev being up. If Jev integration eats too much time, ship the rule-based version behind the same interface and call it the decision layer.

## 9. Demo scenario (what the demo must show)

Prompt: **"Build a landing page with a waitlist form."**

1. Queen asks about audience, style and form fields.
2. Research bee pulls current form-handling docs via TinyFish.
3. Frontend and backend bees build in parallel, messaging each other.
4. Scribe posts each stage to the honeycomb whiteboard in real time.
5. QA bee submits the form in a real browser via TinyFish and reports pass or fail with evidence.
6. User approves or redirects from the whiteboard.

If time runs short, cut scope in this order: ops/docs lanes first, then Jev (use rules), then extra lanes. Never cut: queen interview, at least two workers talking, the live whiteboard, one real TinyFish call (ideally the QA browser test).

## 10. Priorities for the 24 hours

1. End-to-end happy path for the demo scenario, even if ugly.
2. Live whiteboard that visibly updates while agents work (this is the wow moment).
3. Real TinyFish usage on screen.
4. Decision layer (Jev or rules) visible in at least one place, such as an approval gate.
5. Polish, mascots, animations.

## 11. Working rules for agents and teammates

- Small, frequent commits with clear messages. Commit history shows we built this during the hack.
- Do not add dependencies or frameworks without asking. No CrewAI or heavy agent frameworks.
- Keep agents' messages structured (sender, lane, type, content) so the scribe and whiteboard can consume them.
- Prefer the simplest thing that works for the demo. Mark shortcuts with `TODO(post-hack)`.
- No secrets in the repo.
- If a requirement is ambiguous, state your assumption in the PR or commit message and continue, rather than blocking.

## 12. Known unknowns (update as we learn)

- Exact Jev access method and limits.
- TinyFish rate limits and latency in practice.
- Final judging criteria and demo format.
- Repo structure (suggested: `app/` for Tauri + React, `sidecar/` for FastAPI agents, `docs/` for notes).

## 13. Longer-term direction (do not build now)

After the hackathon: a team version where a PM submits a feature request, agents decompose it, and the whiteboard gives stakeholders plain-English progress. Target price in the range of $20 to $40 per user per month. Not part of this hack.

## 14. No prior code (hard rule)

Everything in this repo must be written fresh during the hackathon. Do not copy, paste, port or adapt code, components, configs or plans from any earlier project or repository. Using official docs, public libraries and standard starter templates is fine. This file is the only plan to follow.
