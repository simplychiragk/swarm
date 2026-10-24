# Swarm 🐝

> *A team of AI agents that builds with you, in the open.*

Built for HackIIITD (Esya '26) powered by TinyFish.

Swarm provides a collaborative desktop workspace where a team of specialized AI agents (Queen, Workers, Scribe, QA, Research) constructs software projects while the user observes and steers in real time via a Honeycomb Whiteboard.

---

## Quickstart

### 1. Start the Sidecar
```powershell
# In terminal 1 (starts offline mock mode by default)
python -m uvicorn sidecar.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start the Desktop App
```powershell
# In terminal 2
cd app
npm run tauri dev
```
*(For web preview without compiling Tauri: run `npm run dev` in `app/` and open `http://localhost:1420`)*.

---

## Documentation Links

- **[Project Context & Rules](docs/SWARM_CONTEXT.md)**: Shared source of truth for the project.
- **[WebSocket Contracts](docs/CONTRACT.md)**: Exact event envelope specifications for server and client communication.
- **[Runbook](docs/RUNBOOK.md)**: Setup, running modes, environment variables reference, and troubleshooting.
- **[Development Progress Log](docs/PROGRESS.md)**: Chronological stage-by-stage engineering status and logs.

---

## Repository Structure

- `app/`: Tauri v2 + React + Vite frontend client.
- `sidecar/`: FastAPI backend with WebSockets, agent orchestration runtime, and decision layer.
- `shared/`: Canonical JSON Schemas and TypeScript contracts.
- `docs/`: Comprehensive project documentation.
