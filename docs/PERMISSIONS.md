# Swarm Permission & Policy System

This document specifies Swarm's deterministic, tier-based permission and execution safety architecture.

---

## 1. Core Principle

**Agents never execute tools directly.**

Every tool call—file reads and writes, command execution, TinyFish web search, fetch and browser tasks, git operations, tunnels, or network calls—must pass through a single, centralized `ToolExecutor`.

```mermaid
sequenceDiagram
    participant Agent as Agent (Worker / Bee)
    participant TE as ToolExecutor
    participant PE as PolicyEngine
    participant DL as DecisionLayer (Jev / Rules)
    participant UI as Desktop App (Approval Modal)
    participant DB as SQLite Audit Trail
    participant CR as Safe Subprocess / Tool Handler

    Agent->>TE: execute(tool, args, context)
    TE->>PE: check(agent, tool, args, context)
    
    alt FORBIDDEN
        PE-->>TE: Decision(deny, FORBIDDEN)
        TE->>DB: record_permission_event(denied)
        TE-->>Agent: ToolResult(error="Action forbidden by policy")
    else HIGH
        PE-->>TE: Decision(ask, HIGH)
        TE->>UI: approval_request event
        UI-->>TE: approval_response(approve / redirect / scope)
        alt Approved
            TE->>CR: run_safe_command / handler
            CR-->>TE: CommandResult
            TE->>DB: record_permission_event(approved)
            TE-->>Agent: ToolResult(output)
        else Denied / Timed Out
            TE->>DB: record_permission_event(denied)
            TE-->>Agent: ToolResult(error="User denied / timed out")
        end
    else MEDIUM
        PE->>DL: advise(tool, args) [Optional]
        PE-->>TE: Decision(ask or allow, MEDIUM)
        alt Strict Mode (ask)
            TE->>UI: approval_request
            UI-->>TE: approval_response
        end
        TE->>CR: run_safe_command / handler
        TE->>DB: record_permission_event
        TE-->>Agent: ToolResult
    else LOW
        PE-->>TE: Decision(allow, LOW)
        TE->>CR: run handler
        TE->>DB: record_permission_event(allowed)
        TE-->>Agent: ToolResult(output)
    end
```

---

## 2. Permission Tiers

| Tier | Policy Engine Outcome | Bypassable by Env / Config? | Examples |
|---|---|---|---|
| `FORBIDDEN` | `deny` | **NO. Never.** | Reading or writing `.env`, `.git/`, SSH keys (`~/.ssh`), credentials (`aws`, `kube`, `vault`); destructive commands (`rm -rf /`, `mkfs`, `format`, `dd`); privilege escalation (`sudo`, `doas`, `runas`, `su`); shell builtins (`eval`, `powershell -enc`, `bash -c` raw execution); editing policy file (`sidecar/permissions/policy.json`). |
| `HIGH` | `ask` | **No** (interactive user approval always required). | Any binary/command not explicitly on the allowlist; outbound network tunnels (Cloudflare tunnel, ngrok, localtunnel); publishing packages (`npm publish`, `twine upload`); production deployments (`vercel --prod`, git pushes to protected branches); destructive git operations (`git push --force`, `git reset --hard`). |
| `MEDIUM` | `ask` (in `strict` mode) / `allow` (in `demo` mode) | Yes (can be pre-approved for whole run via `"run"` scope, or auto-allowed in demo mode). | Allowlisted command execution (`npm test`, `pytest`, `git commit`, `python -m`); TinyFish web fetch (`tinyfish_fetch`) and automated browser actions (`tinyfish_browser_task`); reading external project docs outside run workspace. |
| `LOW` | `allow` | Yes (automatic). | File reads and writes strictly contained within `workspace/<run_id>/`; TinyFish search queries (`tinyfish_search`); in-memory agent messaging. |

---

## 3. Escalation Rules

Policy decisions are dynamic and context-aware:
1. **Web-Derived Command Escalation**: If an agent attempts to execute a command containing arguments or scripts downloaded directly from the web (or if `context.web_derived == True`), `MEDIUM` tier actions are automatically escalated to `HIGH` tier.
2. **Budget Limits**: Each run tracks total tool executions. If an agent exceeds `max_tool_calls_per_run` (default: 100), all further actions are denied.
3. **Repeated Denials**: 3 consecutive user denials on the same tool immediately demote that tool to `FORBIDDEN` for the remainder of the run.

---

## 4. Path Sandboxing & Run Workspace Jail

All file access is validated via `resolve_safe_path(run_id, target_path)`:
- Every active run operates within an isolated workspace directory: `workspace/<run_id>/`.
- Path traversal sequences (`..`, `\..`, `/../`) and symlink escapes pointing outside `workspace/<run_id>/` raise `PathSafetyError` and are immediately rejected.
- Access to root repository files, secrets (`.env`, `.git`), and system paths is strictly prohibited.
- Artifact downloads via `GET /runs/{run_id}/artifacts/{artifact_path}` validate path confinement before serving files.

---

## 5. Subprocess Isolation & Child Process Sanitization

All command execution runs via `run_safe_command(argv, cwd, env, timeout_s, max_output_chars)`:
- **No `shell=True`**: Commands must be passed as explicit argv lists (`["npm", "test"]`), completely eliminating shell injection vulnerabilities (`&&`, `;`, `|`, `$(...)`).
- **Scrubbed Environment**: Child processes inherit only a minimal allowlist of system variables (`PATH`, `SYSTEMROOT`, `TEMP`, `USERPROFILE`, `HOME`, `LANG`). All `SWARM_*` environment variables, API keys, tokens, and credentials are wiped from the child process environment.
- **Process Tree Killing**: If a command exceeds its timeout (default: 30s), the entire process tree is terminated using `taskkill /F /T /PID <pid>` on Windows or process group `SIGKILL` on POSIX systems.
- **Output Truncation**: Stdout and stderr are limited (default: 100,000 characters) to prevent memory exhaustion from runaway loops.

---

## 6. Secret Redaction Engine

The redaction engine (`redact(text)` and `redact_data(dict_or_list)`) scrubs sensitive strings:
- Built-in regex patterns detect API keys:
  - OpenAI / OpenRouter (`sk-...`, `sk-or-v1-...`)
  - NVIDIA NIM (`nvapi-...`)
  - AWS Access Keys (`AKIA[0-9A-Z]{16}`)
  - GitHub Personal Access Tokens (`ghp_...`, `github_pat_...`)
  - Generic Bearer tokens, private keys (`-----BEGIN PRIVATE KEY-----`), and JWTs
- Ambient redaction: Any active environment variable containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, or starting with `SWARM_` has its literal value redacted as `[REDACTED_SECRET]`.
- Redaction is applied automatically across:
  - WebSocket `feed_message` broadcasts
  - Approval prompts and argument previews
  - Whiteboard cards
  - Subprocess stdout and stderr
  - SQLite audit trail records

---

## 7. Approval Scope & Interactive User Modal

When an action requires user sign-off (`HIGH` tier or `MEDIUM` tier in strict mode):
- An `approval_request` event is dispatched via WebSocket to the desktop shell containing:
  - `tool`: Target tool name (e.g. `command_run`)
  - `args_preview`: Scrubbed, redacted preview of arguments (e.g. `{"command": ["npm", "install", "stripe"]}`)
  - `risk`: Risk level (`HIGH` or `MEDIUM`)
  - `reason`: Explanation of why approval is needed
  - `scope_options`: Permitted scope choices: `["once", "run", "deny"]`
  - `expires_in_s`: Timeout before the request is auto-denied (default: 120s)
- **Scope Options**:
  - `once`: Authorizes this single tool invocation.
  - `run`: Authorizes this tool and exact arguments for the remainder of the current run (only valid for `MEDIUM` tier; attempting to grant `run` scope to `HIGH` tier is automatically capped at `once`).
  - `deny`: Rejects the tool call.

---

## 8. Audit Trail (SQLite)

Every policy check and tool execution is recorded in a SQLite database (`workspace/swarm_audit.db` or `SWARM_DB_PATH`):
- Table `permission_events`:
  - `id`: Auto-incrementing primary key
  - `timestamp`: ISO 8601 timestamp
  - `run_id`: Associated run identifier
  - `agent`: Invoking agent name
  - `tool`: Target tool name
  - `tier`: `FORBIDDEN` | `HIGH` | `MEDIUM` | `LOW`
  - `decision`: `allow` | `ask` | `deny`
  - `reason`: Rationale behind decision
  - `args_scrubbed`: JSON-serialized, redacted arguments
  - `approved_by`: `auto` | `user` | `none`
  - `duration_ms`: Execution duration in milliseconds
  - `status`: `success` | `denied` | `timed_out` | `error`
- Queryable via REST endpoint: `GET /runs/{run_id}/permissions`.

---

## 9. Operational Modes

Configurable via `SWARM_PERMISSION_MODE`:
- `strict` (Default): All `HIGH` and `MEDIUM` tier actions require interactive user approval.
- `demo`: All `MEDIUM` tier actions (allowlisted commands, TinyFish fetch/browser tasks) are auto-approved to enable smooth 24-hr hackathon demos. `HIGH` tier actions still require interactive approval. `FORBIDDEN` actions can **never** be executed under any mode.

---

## 10. How to Add a Tool or Edit Policy

1. Open `sidecar/permissions/policy.json`.
2. To allow a binary under allowlisted command execution, add it to `allowlisted_commands` with optional permitted subcommands:
   ```json
   "allowlisted_commands": {
     "cargo": {
       "allowed_subcommands": ["check", "test", "build"]
     }
   }
   ```
3. To assign a new tool to a tier, add it to the corresponding list under `tiers`:
   ```json
   "tiers": {
     "LOW": ["file_read", "file_write", "tinyfish_search", "my_new_low_tool"],
     "MEDIUM": ["tinyfish_fetch", "tinyfish_browser_task", "command_run"],
     "HIGH": ["tunnel_create", "deploy_production", "git_push"],
     "FORBIDDEN": ["policy_edit", "env_read"]
   }
   ```
4. If a tool is not listed in `policy.json`, it is rejected by default as `FORBIDDEN`.

---

## 11. Known Limits: Guardrails, Not a Sandbox

> [!WARNING]
> **Known Limits: Guardrails, not a sandbox; use containers or VMs for real deployments.**

Swarm's permission system provides **application-level guardrails**:
- Deterministic policy tiers
- Path containment within `workspace/<run_id>/`
- Child process environment scrubbing
- Token and API key redaction
- Subprocess argv execution without shell evaluation

However, **in-process software guardrails cannot prevent kernel-level or OS-level sandbox escapes**:
1. **Host OS Shared Kernel**: Child processes run on the host operating system with the permissions of the user running Swarm.
2. **File Descriptors and Memory**: While environment variables are scrubbed, malicious binaries could attempt OS privilege escalation or inspect process memory if run on unisolated hardware.
3. **Network Isolation**: Outbound network requests (from commands or tools) are governed by policy tiers, but are not blocked at the host network namespace level.

**Production Deployment Recommendation**:
For production environments or multi-tenant agent execution, Swarm must be deployed within isolated containers or virtual machines (e.g., Docker with rootless containers, gVisor, Firecracker microVMs, or Windows Sandbox / WSL2 containers) with dedicated network bridges and read-only root filesystems.
