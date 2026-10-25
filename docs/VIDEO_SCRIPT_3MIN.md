# 🎬 Swarm: 3-Minute Video Demo Script & Screen Walkthrough

> **Total Duration**: 3:00 (180 seconds)  
> **Target Audience**: HackIIITD Judges, Technical Evaluators, Open Source Community  
> **Key Focus**: Transparency (Honeycomb Whiteboard), Interactive MCQ Discovery, TinyFish Live Verification, Local Codebase Harness (`file_edit`), and Live Git Diff Approval Gating.

---

## ⏱️ Timeline Overview

```
0:00 ─── 0:25 ─── 0:55 ─── 1:30 ─── 2:05 ─── 2:40 ─── 3:00
 │         │        │        │        │        │        │
 └─ Hook   └─ Discovery └─ Parallel └─ Browser QA └─ Local Diff └─ Wrap-up
```

---

## 🎥 Second-by-Second Production Script

---

### [0:00 - 0:25] ACT I: The Hook & The Multi-Agent Coding Problem
- **Visual**: Full-screen capture of the Swarm desktop application with the dark amber Honeycomb Whiteboard empty and pulsing with honeycomb hex lines.
- **Presenter (Voiceover / Webcam in corner)**:
  > *"Every AI coding tool today operates like an opaque black box: you type a prompt, wait three minutes, and pray the code works. You can't see why decisions were made, models hallucinate outdated APIs, and code is marked 'done' without running in a real browser.*
  >
  > *This is **Swarm**: a multi-agent software engineering farm where a Queen, specialized Workers, and TinyFish web agents build and verify software in the open—while you observe and steer in real time."*

---

### [0:25 - 0:55] ACT II: Interactive MCQ Discovery & Live Grounding
- **Action on Screen**:
  1. Presenter clicks the prompt box at the bottom left.
  2. Types: `Create a modern landing page for a developer networking event at IIIT Delhi.` and hits Enter.
  3. Queen Bee responds in the Nectar feed with an interactive Multiple Choice Question:
     - `Who is your target audience?`
     - Chips rendered: `[A] College Students & Hackers`, `[B] Early-stage Founders`, `[C] Developers & Open Source Community`, `[ ✏️ Type your own answer... ]`.
  4. Presenter clicks `[A] College Students & Hackers` without typing.
  5. Queen asks for aesthetic style; presenter clicks `[A] Dark Honeycomb & Cyberpunk Amber`.
- **Presenter (Voiceover)**:
  > *"Notice how the Queen doesn't just blindly dump code. She immediately initiates a structured discovery interview with interactive Multiple Choice chips. With a single click, I select our audience and aesthetic.
  >
  > Next, our Research Bee uses the **TinyFish Search & Fetch API** to pull live, 2026 design references and schema standards from the web so our agents never rely on stale training memory."*

---

### [0:55 - 1:30] ACT III: Parallel Construction, Contract Negotiation & Scribe
- **Action on Screen**:
  1. Highlight the Nectar Feed: Backend Worker and Frontend Worker start executing tasks in parallel.
  2. BE Worker emits: `Locked API contract: POST /api/register -> Request/Response 201`.
  3. FE Worker acknowledges and hooks up its `app.js` fetch client.
  4. Zoom in on the Honeycomb Whiteboard: The Scribe Bee is continuously condensing 20+ turns of raw developer chatter into clean, structured **Honey Cards** across the `BE`, `FE`, and `TEST` lanes.
- **Presenter (Voiceover)**:
  > *"Now watch our Backend and Frontend Workers build in parallel. They aren't isolated—they talk to each other across channels, agreeing on API contracts and locking schema shapes before writing a single line.
  >
  > Meanwhile, our **Scribe Bee** filters out low-level developer chatter and projects clean, high-level milestone cards onto the Honeycomb Whiteboard. Any stakeholder can look at this board and understand exactly what is happening in real time."*

---

### [1:30 - 2:05] ACT IV: TinyFish Browser QA & Closed-Loop Verification
- **Action on Screen**:
  1. Click on the `QA & Verification` card under the `TEST` lane.
  2. Open the Proof Modal: Shows the TinyFish headless browser agent navigating to the live preview endpoint (`http://127.0.0.1:8000/runs/run-default/preview/`).
  3. Show the browser fill the form, submit the payload, and capture a verified screenshot evidence item confirming HTTP 201 and visual toast banner.
- **Presenter (Voiceover)**:
  > *"Most agent tools consider code 'complete' the second the file hits disk. Swarm refuses to call code done until our **TinyFish QA Bee** spins up a real headless browser session, navigates the live running app, submits test payloads, and verifies the DOM response with visual screenshot proof.
  >
  > If a button is broken or an endpoint throws 500, the Queen detects the failure, routes it back to the responsible worker, applies a patch, and re-tests until verified."*

---

### [2:05 - 2:40] ACT V: Local Codebase Harness & Live Git Diff Approval Gate
- **Action on Screen**:
  1. The **Production Release Gate** modal pops open automatically.
  2. Show the brand-new **Live Working-Tree Git Diff** inside the modal:
     - Clear green `+` additions and red `-` deletions displaying `api/main.py` and `index.html`.
  3. Point out that Swarm is attached to an external codebase via `SWARM_PROJECT_ROOT`, issuing targeted line-level search-and-replace patches (`file_edit`) rather than overwriting existing repositories.
  4. Point to the action buttons: `[Approve & Apply]` vs `[Reject & Revert]`.
  5. Presenter clicks **`Approve & Apply`**. Confetti fires, card turns green (`DONE`), and status announces deployment live.
- **Presenter (Voiceover)**:
  > *"Swarm isn't just a sandboxed prototype builder—it is a full local coding agent harness. Point it at any existing repository on your laptop with `SWARM_PROJECT_ROOT`. Workers use codebase exploration (`search_code`, windowed `file_read`) and issue targeted line-level patches with automatic self-correcting test loops.
  >
  > And before anything touches your production branch, the Jevons approval gate shows a live, syntax-highlighted **Git Diff**. You can inspect the exact code changes and choose to **Approve & Apply** or **Reject & Revert** in one click."*

---

### [2:40 - 3:00] ACT VI: Conclusion & Call to Action
- **Visual**: Switch to a split view of the Swarm Whiteboard, live running preview website, and terminal showing 80 passing unit tests.
- **Presenter (Voiceover)**:
  > *"Swarm combines multi-agent parallelism, real-web grounding via TinyFish, verifiable browser testing, and human-in-the-loop safety.
  >
  > Software engineering with AI shouldn't be an opaque gamble—it should be an open, verified team sport.
  >
  > Thank you! Check out Swarm on GitHub."*
- **Final Frame**: Swarm GitHub URL, Team Credits (Chirag Kumar, Tanmay Sharma, Priyanshu Tiwari), HackIIITD & TinyFish logos.

---

## 🛠️ Pre-Recording Checklist

1. **Sidecar in Live Mode**:
   ```powershell
   $env:SWARM_MODE="live"
   $env:SWARM_LLM_MODE="live"
   npm run sidecar
   ```
2. **Frontend UI**:
   - `npm run app` (or `npm run app:web` in fullscreen Chrome).
   - Ensure the connection badge reads **CONNECTED** (green dot).
3. **Screen Resolution**: Set display to **1080p (1920x1080)** with 100% or 125% DPI scale for crisp text.
4. **Practice Prompt**: Use the exact prompt: `Create a modern landing page for a developer networking event at IIIT Delhi.`
