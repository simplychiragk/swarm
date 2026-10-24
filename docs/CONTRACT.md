# Swarm WebSocket Event Contract

All communication between the Tauri/React desktop app and the FastAPI sidecar occurs over the WebSocket endpoint:
`ws://127.0.0.1:8000/ws`

Every message is wrapped in an `EventEnvelope`:
```json
{
  "event": "<event_name>",
  "payload": { ... }
}
```

---

## Event Summary Table

| Event Name | Direction | Description |
|---|---|---|
| `feed_message` | Server -> Client | Live agent chatter, tasks, status, evidence, or errors |
| `card_upsert` | Server -> Client | Honeycomb whiteboard summary card creation or update |
| `approval_request` | Server -> Client | User authorization gate triggered by queen or decision layer |
| `user_message` | Client -> Server | User chat, answer to interview question, or instruction |
| `approval_response` | Client -> Server | User decision on an active approval request |

---

## Detailed Event Specifications

### 1. `feed_message` (Server -> Client)
Raw message passing through the live swarm feed ("nectar").

#### Fields:
- `id` (string, required): Unique UUID for the message.
- `timestamp` (string, required): ISO 8601 formatted timestamp.
- `sender` (enum, required): `"queen"` | `"worker"` | `"scribe"` | `"qa"` | `"research"` | `"system"`
- `lane` (enum, required): `"FE"` | `"BE"` | `"DB"` | `"Design"` | `"Test"` | `"Docs"` | `"Ops"` | `"none"`
- `type` (enum, required): `"chat"` | `"task"` | `"status"` | `"evidence"` | `"error"`
- `content` (string, required): Text content of the message.
- `metadata` (object, optional): Arbitrary metadata key-values (tool name, query, duration, etc.).

#### Example:
```json
{
  "event": "feed_message",
  "payload": {
    "id": "msg-101",
    "timestamp": "2026-10-24T12:00:00.000Z",
    "sender": "worker",
    "lane": "FE",
    "type": "chat",
    "content": "FE Worker: Scaffolding waitlist hero section with responsive Tailwind inputs.",
    "metadata": {
      "framework": "react",
      "component": "WaitlistHero"
    }
  }
}
```

---

### 2. `card_upsert` (Server -> Client)
Synthesized progress cards posted by the Scribe to the Honeycomb Whiteboard ("honey").

#### Fields:
- `id` (string, required): Unique card identifier (e.g. `card-fe-hero`).
- `title` (string, required): Concise headline for the whiteboard card.
- `summary` (string, required): Plain-language summary of completed or ongoing work.
- `status` (enum, required): `"planned"` | `"in_progress"` | `"done"` | `"needs_approval"` | `"failed"`
- `lane` (enum, required): `"FE"` | `"BE"` | `"DB"` | `"Design"` | `"Test"` | `"Docs"` | `"Ops"` | `"none"`
- `evidence` (array of objects, optional): Verification items, each having:
  - `kind` (string, required): Evidence category (e.g. `"screenshot"`, `"api_call"`, `"test_log"`).
  - `url_or_text` (string, required): URL or textual detail.
- `updated_at` (string, required): ISO 8601 timestamp of update.

#### Example:
```json
{
  "event": "card_upsert",
  "payload": {
    "id": "card-qa-1",
    "title": "Browser QA Verification (TinyFish)",
    "summary": "Form submission verified in a real browser session. Status 201 received.",
    "status": "done",
    "lane": "Test",
    "evidence": [
      {
        "kind": "screenshot",
        "url_or_text": "https://tinyfish-demo.s3.amazonaws.com/evidence/waitlist.png"
      }
    ],
    "updated_at": "2026-10-24T12:02:15.000Z"
  }
}
```

---

### 3. `approval_request` (Server -> Client)
Presents a critical action to the user for interactive sign-off.

#### Fields:
- `id` (string, required): Unique identifier for the approval request.
- `card_id` (string, required): WhiteboardCard ID awaiting sign-off.
- `prompt` (string, required): Question or decision displayed to user.
- `options` (array of strings, required): Button choices (e.g. `["Approve", "Redirect"]`).
- `lane` (enum, required): `"FE"` | `"BE"` | `"DB"` | `"Design"` | `"Test"` | `"Docs"` | `"Ops"` | `"none"`
- `card` (object, optional): Embedded snapshot of the target WhiteboardCard.
- `created_at` (string, required): ISO 8601 timestamp when request was generated.
- `tool` (string, optional): Target tool name requiring authorization (e.g. `"command_run"`).
- `args_preview` (object, optional): Scrubbed, redacted preview of arguments.
- `risk` (string, optional): Risk tier (`"HIGH"` | `"MEDIUM"`).
- `reason` (string, optional): Rationale explaining why authorization is required.
- `agent` (string, optional): Requesting agent identifier (e.g. `"worker_fe"`).
- `scope_options` (array of strings, optional): Permitted scopes: `["once", "run", "deny"]`.
- `expires_in_s` (number, optional): Timeout in seconds before auto-denial (default: `120`).

#### Example:
```json
{
  "event": "approval_request",
  "payload": {
    "id": "appr-deploy-99",
    "card_id": "card-approval",
    "prompt": "Worker FE requests to run command: npm install stripe. Approve?",
    "options": ["Approve", "Redirect"],
    "lane": "Ops",
    "created_at": "2026-10-24T12:03:00.000Z",
    "tool": "command_run",
    "args_preview": {
      "command": ["npm", "install", "stripe"]
    },
    "risk": "HIGH",
    "reason": "Non-allowlisted command execution requires authorization",
    "agent": "worker_fe",
    "scope_options": ["once", "run", "deny"],
    "expires_in_s": 120
  }
}
```

---

### 4. `user_message` (Client -> Server)
Inbound message sent from the user via the desktop client UI.

#### Fields:
- `id` (string, required): Unique client message ID.
- `text` (string, required): User's prompt, answer, or instruction.
- `timestamp` (string, required): ISO 8601 timestamp from client.

#### Example:
```json
{
  "event": "user_message",
  "payload": {
    "id": "user-msg-1",
    "text": "Target audience is developers; use dark mode with honeycomb patterns; capture name and email.",
    "timestamp": "2026-10-24T12:00:30.000Z"
  }
}
```

---

### 5. `approval_response` (Client -> Server)
Inbound user response resolving an active approval request.

#### Fields:
- `approval_id` (string, required): Identifier of the approval request being answered.
- `card_id` (string, required): Associated WhiteboardCard ID.
- `decision` (enum, required): `"approve"` | `"redirect"`
- `note` (string, optional): Context or revision instructions if redirected.
- `scope` (enum, optional): `"once"` | `"run"` | `"deny"` (defaults to `"once"` on approval)

#### Example:
```json
{
  "event": "approval_response",
  "payload": {
    "approval_id": "appr-deploy-99",
    "card_id": "card-approval",
    "decision": "approve",
    "scope": "run",
    "note": "Looks great, approved for this run."
  }
}
```

---

## REST Endpoints

In addition to the WebSocket endpoint, the sidecar exposes REST endpoints for run artifacts and permission audits:

### 1. `GET /runs/{run_id}/permissions`
Retrieves the recorded SQLite permission audit trail for the specified `run_id`.

**Response (JSON)**:
```json
[
  {
    "id": 1,
    "timestamp": "2026-10-24T12:01:00.000Z",
    "run_id": "run-101",
    "agent": "worker_fe",
    "tool": "file_write",
    "tier": "LOW",
    "decision": "allow",
    "reason": "Allowed by tier LOW",
    "args_scrubbed": "{\"path\": \"src/App.tsx\"}",
    "approved_by": "auto",
    "duration_ms": 1.2,
    "status": "success"
  }
]
```

### 2. `GET /runs/{run_id}/artifacts/{artifact_path:path}`
Safely retrieves an artifact file created during a run. Path traversal (`..`) outside `workspace/{run_id}/` is strictly rejected with HTTP 403.

### 3. `GET /workspace/tree` or `GET /runs/{run_id}/tree`
Returns all files in the active run's workspace (`workspace/<run_id>/`) formatted for the UI file explorer:
```json
{
  "run_id": "run-default",
  "workspace": "workspace/run-default",
  "files": [
    {
      "name": "App.tsx",
      "path": "src/App.tsx",
      "language": "typescript",
      "content": "...",
      "size": 1024
    }
  ],
  "count": 1
}
```

### 4. `PUT /workspace/files/{file_path:path}` or `PUT /runs/{run_id}/files/{file_path:path}`
Saves updated file content to the run's workspace via `ToolExecutor` (audited, path-safe, non-traversal):
**Request**: `{"content": "new code here"}`
**Response**: `{"success": true, "path": "src/App.tsx", "bytes": 1024}`

### 5. `POST /workspace/files` or `POST /runs/{run_id}/files`
Creates a new file or directory inside the run workspace:
**Request**: `{"path": "src/components/Header.tsx", "content": "export ...", "is_directory": false}`
**Response**: `{"success": true, "path": "src/components/Header.tsx", "is_directory": false}`


