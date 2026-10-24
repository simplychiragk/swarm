# Swarm Steering & Real-Time Redirection Guide

Swarm enables real-time user steering while agents are mid-build. The user is an active collaborator rather than a passive observer.

---

## 1. Input Modes

Clients can send `user_message` events with an optional `mode` property:

```typescript
export interface UserMessage {
  id: string;
  text: string;
  timestamp: string; // ISO 8601
  mode?: 'steer' | 'queue' | 'interrupt'; // Default: 'steer'
}
```

### Steering Modes Overview

| Mode | Behavior | When to Use |
|---|---|---|
| **`steer` (default)** | Injected immediately into the active swarm. Queen evaluates the prompt, computes a structured `plan_diff`, broadcasts the diff, informs worker lanes, and modifies workspace code. | Adding a new form field, altering UI copy, requesting an additional API route, or modifying styling. |
| **`queue`** | Appended to the Queen's pending queue. Queen acknowledges receipt in the status feed and holds instructions until the active build phase completes. | Backlog tasks or suggestions meant for subsequent iterations without disturbing current work. |
| **`interrupt`** | Immediately pauses active worker tasks. Queen emits an interrupt status and whiteboard card, holding execution for user clarification. | Emergency halts, stopping an unintended action, or resetting context. |

---

## 2. Plan Diff Contract & Event Shape

When steering triggers plan changes, the Queen computes a `PlanDiff` and emits a `plan_diff` WebSocket event:

```json
{
  "event": "plan_diff",
  "payload": {
    "run_id": "run-default",
    "reason": "User steering: Wait, add a phone number field too, with country code",
    "timestamp": "2026-10-24T18:00:00Z",
    "changes": [
      {
        "task_id": "task-fe-phone",
        "title": "Add Phone Number & Country Code Selector",
        "action": "added",
        "lane": "FE",
        "reason": "Capture verified international phone number with country code picker"
      },
      {
        "task_id": "task-be-phone",
        "title": "Extend Waitlist Schema for Phone Validation",
        "action": "added",
        "lane": "BE",
        "reason": "Accept and validate optional phone & country_code in POST /api/waitlist"
      },
      {
        "task_id": "task-qa-verify",
        "title": "Verify Form Submission with Phone Field",
        "action": "modified",
        "lane": "Test",
        "reason": "Verify submission succeeds with name, email, role, and phone number"
      }
    ]
  }
}
```

### Whiteboard Synchronization
1. Scribe reflects plan modifications on the Whiteboard as updated cards with the **`[EDITED]`** prefix in title or summary.
2. The active plan card `card-steer-plan` is emitted with status `in_progress`.

---

## 3. Worker Workspace Integration

When a `steer` diff is applied:
1. **Frontend Worker (`fe_worker`)**:
   - Updates `index.html` with the new DOM elements (e.g. `<input type="tel" id="phone" />` and `<select id="country-code">`).
   - Updates `app.js` to extract the phone value and payload properties.
   - Emits card update for `task-fe-hero` with `[EDITED]` badge.
2. **Backend Worker (`be_worker`)**:
   - Updates `api/main.py` Pydantic models (`WaitlistRequest`) with optional `phone` and `country_code` attributes.
   - Updates response payload schema.
   - Emits card update for `task-be-api` with `[EDITED]` badge.
3. **QA Bee (`qa_bee`)**:
   - Retests form submission asserting that phone and country code inputs are validated and submitted.

---

## 4. SQLite Audit & REST API

Every steering action generates an immutable audit receipt in SQLite:

- Table: `steers` (`id, run_id, message_id, mode, status, prompt, plan_diff_json, targets_json, timestamp`)
- Endpoint: `GET /runs/{run_id}/steers`

Example Response:
```json
{
  "run_id": "run-default",
  "count": 1,
  "steers": [
    {
      "id": "steer-a8f391",
      "run_id": "run-default",
      "message_id": "msg-steer-1",
      "mode": "steer",
      "status": "applied",
      "prompt": "Wait, add a phone number field too, with country code",
      "plan_diff": {
        "reason": "User steering: Wait, add a phone number field too, with country code",
        "changes": [ ... ]
      },
      "targets": ["fe_worker", "be_worker"],
      "timestamp": "2026-10-24T18:00:00Z"
    }
  ]
}
```
