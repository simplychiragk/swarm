# 📊 Swarm: 8-Slide Pitch Deck Specification

> **Event**: HackIIITD Final (Esya '26, IIIT Delhi) • Powered by **TinyFish**  
> **Format**: 8 Slides (16:9 Widescreen)  
> **Team**: Chirag Kumar, Tanmay Sharma, Priyanshu Tiwari  
> **Pitch Duration**: ~4-5 Minutes

---

## Slide 1: Title & Vision

### Header
# Swarm 🐝
### Subtitle
**A Desktop Multi-Agent Software Engineering Farm That Builds, Verifies, and Refactors Code in the Open.**

---

### Visual Layout
- **Left Column**: Clean amber/dark honeycomb hex graphics with bee lane badges (`👑 Queen`, `🐝 Workers`, `📜 Scribe`, `🔍 TinyFish QA`).
- **Right Column**: Live screenshot of the Honeycomb Whiteboard dashboard with connected status badge.
- **Footer**: `HackIIITD 2026 Final • Powered by TinyFish • Team Swarm`

### Bullet Points / Callouts
- **The One-Liner**: *A team of specialized AI agents that builds with you, in real time, with zero black boxes.*
- **Core Pillars**: Visibility • Freshness • Verification • Human Control.

### Speaker Notes
> "Good morning, judges. We are team Swarm. Today, AI coding is moving from single-turn chat autocomplete into teams of autonomous agents. But current agent frameworks operate as opaque black boxes: you type a prompt, wait minutes, and pray the code works without knowing why decisions were made or whether the code was ever tested. Swarm turns agent software engineering into an open, verifiable team sport where you watch and steer in real time."

---

## Slide 2: The Multi-Agent Coding Crisis

### Header
## The 4 Fatal Flaws of Black-Box AI Coding

---

### Visual Layout
4-Quadrant comparison grid with warning icons highlighting industry pain points.

| Quadrant | The Industry Flaw | The Practical Consequence |
| :--- | :--- | :--- |
| **1. The Black Box** | Multi-agent decisions, task delegations, and internal debate are completely hidden from the user. | Developers lose trust; non-technical teammates cannot follow progress. |
| **2. Stale Model Memory** | Agents write code using frozen model weights from months or years ago. | Hallucinated syntax, deprecated package versions, and broken API calls. |
| **3. Unverified Claims** | Agents declare tasks "DONE" as soon as a file is written to disk. | Broken buttons, runtime crashes, and unhandled server errors discoverable only by users. |
| **4. Lack of Steerability** | Once launched, agent swarms cannot be steered, interrupted, or diff-reviewed before changes land. | Destructive file overwrites with no granular human-in-the-loop safety. |

### Speaker Notes
> "If you look at the state of AI coding tools today, they suffer from four fundamental flaws: opacity, stale memory, unverified claims, and zero granular steering. When an agent marks a task 'complete', nobody actually verified that the endpoint returned 201 or that the button works in a browser. Swarm was designed from the ground up to solve all four flaws."

---

## Slide 3: The Swarm Hive Architecture

### Header
## Autonomous Collaboration with Domain-Specialized Lanes

---

### Visual Layout
System topology diagram showing the React 19 / Tauri v2 frontend communicating over WebSockets with the Python FastAPI Sidecar, with agents communicating asynchronously across domain lanes.

```
                  ┌───────────────────────────────────────────────┐
                  │    React 19 + Tauri v2 Desktop Interface      │
                  │   (Honeycomb Whiteboard + Live Nectar Feed)   │
                  └───────────────────────┬───────────────────────┘
                                          │ Bidirectional WebSocket
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │            FastAPI Sidecar Runtime            │
                  │   MessageBus • DecisionLayer • PolicyEngine   │
                  └───────┬───────────────┬───────────────┬───────┘
                          │               │               │
            ┌─────────────┴─────┐   ┌─────┴───────┐   ┌───┴─────────────┐
            ▼                   ▼   ▼             ▼   ▼                 ▼
      👑 Queen Bee        🐝 BE Worker     🐝 FE Worker   📜 Scribe Bee     🔍 TinyFish QA
   (Interview & Plan)  (FastAPI & Schemas) (HTML & CSS) (Whiteboard Sync) (Browser Proof)
```

### Key Technical Innovations
- **No Heavy Framework Overhead**: Built with an ultra-lightweight custom async event bus (no bloated CrewAI/AutoGPT dependencies).
- **Asynchronous Contract Negotiation**: Backend and Frontend workers lock API schema shapes across channels before code generation.
- **Dual-Model Gateway**: Primary Pollinations AI (`openai/gpt-5.4-nano`) with keyless fallback + OpenRouter multi-model resiliency.

### Speaker Notes
> "Here is our architecture. At the top is our desktop application built in React and Tauri. Below it is our FastAPI sidecar. Inside the hive, our agents operate in specialized domain lanes: Queen interviews and plans; Backend and Frontend workers negotiate and lock API contracts asynchronously; Scribe translates low-level chatter into plain language; and our TinyFish QA Bee validates the running site."

---

## Slide 4: Real-Time Transparency: The Honeycomb Whiteboard

### Header
## From Low-Level Chatter to Stakeholder Clarity

---

### Visual Layout
Side-by-side comparison mockup:
- **Left**: The raw developer chat feed (**Nectar**) showing technical logs, contract negotiations, and the Queen's interactive MCQ choice chips (`[A]`, `[B]`, `[C]`).
- **Right**: The **Honeycomb Whiteboard** showing high-level synthesized milestone cards (**Honey**) categorized across `FE`, `BE`, `TEST`, and `OPS` lanes.

### Key Points
- **Interactive MCQ Discovery**: The Queen asks up to 3 targeted constraint questions formatted with interactive clickable option badges.
- **Scribe Synthesis**: A background Scribe Agent batches chatter, filters noise using a heuristic decision layer, and posts clean cards.
- **Continuous Progress Tracking**: Cards transition in real time: `PLANNED` → `IN_PROGRESS` → `DONE` → `NEEDS_APPROVAL`.

### Speaker Notes
> "Transparency shouldn't mean drowning the user in thousands of lines of terminal logs. We split the interface into two levels of abstraction: On the left is the raw Nectar feed with our new interactive MCQ chips that let users answer requirements in one click. On the right is the Honeycomb Whiteboard, where our Scribe Bee continuously condenses developer chatter into plain-language milestone cards that any stakeholder can understand at a glance."

---

## Slide 5: Fresh & Verified: TinyFish Live Web & Browser QA

### Header
## Grounded Before Build • Verified in Real Browsers After Build

---

### Visual Layout
Split visual showing:
1. **Research Bee** executing TinyFish Search & Fetch to ground form schemas.
2. **QA Bee** launching a real headless browser session against `http://127.0.0.1:8000/runs/.../preview/`.
3. An actual screenshot artifact captured by TinyFish attached directly to the Whiteboard Card.

### Two-Stage TinyFish Grounding Loop
1. **Before Build (Research Bee)**:
   - Queries TinyFish Search & Fetch for current 2026 design standards, Pydantic v2 validation patterns, and modern CSS styles.
   - Eliminates stale hallucination before code is written.
2. **After Build (QA Bee)**:
   - Spins up a real browser instance, fills the form fields with dynamic test payloads, clicks submit, and confirms HTTP 201 response.
   - Captures visual screenshot evidence and attaches DOM assertions directly to the Honeycomb card.
3. **The Gauntlet Suite**:
   - 4 autonomous browser archetypes: Mobile Viewport, Messy Unicode Input, Double-Submit, and Malformed Payloads with HTML audit reports.

### Speaker Notes
> "TinyFish API integration is the backbone of our verification layer. Before our workers write a single line, our Research Bee uses TinyFish Search and Fetch to pull fresh 2026 documentation from the web. And after the build finishes, our QA Bee uses TinyFish's browser agent to physically open the running preview, type into inputs, submit the form, and verify HTTP 201 response codes with screenshot proof. If it fails, Queen routes the failure back to the worker for an automated patch."

---

## Slide 6: Full Local Codebase Agent Harness

### Header
## Beyond Greenfield Sandboxes: Live Repository Refactoring

---

### Visual Layout
Feature diagram showcasing Swarm's new local coding harness capabilities:

```
  Existing Local Repository (SWARM_PROJECT_ROOT)
       ├── Codebase Exploration (search_code, list_directory, windowed file_read)
       ├── Targeted Diff Editing (exact search-and-replace, atomic replacement)
       └── Self-Correcting Test Loop (pytest / npm test auto-healing up to 3x)
```

### Key Engineering Primitives (Native Local Codebase Harness)
- **Attach to Any Repo**: Set `SWARM_PROJECT_ROOT` or `--project-dir` to point Swarm directly at any existing project on your laptop.
- **Targeted Line Diffs (`file_edit`)**: Replaces whole-file overwriting with exact block search-and-replace using atomic temporary file swaps.
- **Codebase Exploration**: Workers search functions with `search_code` (regex) and inspect lines with windowed `file_read` before patching.
- **Self-Correcting Test Loop**: Automatically runs `pytest` or `npm test` after edits; reads tracebacks and iterates on fixes up to 3 cycles.

### Speaker Notes
> "Swarm is not just a toy that generates isolated demo folders. It is a full local coding agent harness. You can point Swarm at any existing repository on your machine. Workers explore your codebase, read existing functions, make targeted line-level search-and-replace diffs without destroying your existing files, and execute your local test suite to heal their own bugs."

---

## Slide 7: Deterministic Safety & Visual Git Diff Approval Gate

### Header
## Human-in-the-Loop Control with Live Code Previews

---

### Visual Layout
High-resolution screenshot of the **Production Release Gate Modal**:
- Showing the unified **Git Diff** viewer with red `-` removals and green `+` additions.
- The two primary action buttons: `[Approve & Apply]` and `[Reject & Revert]`.
- Policy enforcer summary and tool audit stats.

### Deterministic Safety Architecture
- **Policy Engine (`policy.json`)**: Deterministic tool tiers (`ALLOW`, `GATE`, `FORBIDDEN`).
- **Credential Protection**: Automatic regex redaction of `.env*`, `.pem`, `.key`, and secret tokens from all logs and storage.
- **Recoverable Git Revert**: Rejecting a diff executes an isolated `git stash push --include-untracked`, guaranteeing zero unrecoverable code loss.
- **SQLite Audit Trail**: Full recording of every tool call, latency, and provenance (`real` vs `simulated`).

### Speaker Notes
> "Autonomy without safety is dangerous. Swarm enforces a deterministic security policy: sensitive files like .env and private keys are strictly forbidden. And when the project reaches the Production Release Gate, our Approval Modal renders a live, syntax-highlighted unified Git Diff showing every line added or removed. You can inspect the exact code changes and choose to Approve and Apply, or Reject and Revert with a single click."

---

## Slide 8: Technical Stack, Verification & Future Roadmap

### Header
## Production-Ready Verification & What's Next

---

### Visual Layout
Two columns:
- **Left**: Verified test suite metrics & tech stack badges.
- **Right**: Future roadmap and HackIIITD summary.

### Verified Deliverables & Test Metrics
- **80 / 80 Pytest Suite Passing** (agents, decision layer, permissions, and gap implementation).
- **Headless Mock E2E**: 2.62s execution (< 15s budget).
- **Frontend Production Build**: Zero TypeScript or Vite warnings.

### Tech Stack
- **Frontend**: Tauri v2, React 19, Tailwind CSS v4, Lucide Icons.
- **Sidecar**: Python 3.11, FastAPI, WebSockets, SQLite WAL, Pydantic v2.
- **Web Grounding**: TinyFish Search, Fetch & Browser Agent.
- **Models**: Pollinations AI (`openai/gpt-5.4-nano`), OpenRouter (`xingchen-agi`, `nemotron`).

### Future Roadmap
1. **Adversarial Hornet Bee (Red Team)**: Automated security fuzzing & vulnerability patching.
2. **Multi-Repo Workspace Support**: Coordinate microservice swarms across distributed repositories.
3. **Enterprise Git PR Integration**: Direct GitHub / GitLab PR creation with Honeycomb summary cards.

### Speaker Notes
> "To conclude: Swarm is fully verified with 80 automated tests passing, clean production builds, and end-to-end browser execution. We believe the future of AI engineering isn't black-box code generators, but collaborative, transparent swarms that build with you in the open. Thank you, and we'd love to take your questions!"

---
*Slide deck designed for HackIIITD 2026. Built by Chirag Kumar, Tanmay Sharma, and Priyanshu Tiwari.*
