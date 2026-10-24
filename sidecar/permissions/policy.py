"""
Policy Engine for Swarm Permissions.
Deterministic rule evaluation across FORBIDDEN, HIGH, MEDIUM, and LOW tiers.
Enforces execution budgets, web-derived escalation, run-scoped grants,
and strict vs demo mode gating.
"""

import os
import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal, Set, Union

from .redaction import redact
from .path_safety import FORBIDDEN_FILE_PATTERNS, PROTECTED_PROJECT_DIRS


@dataclass
class Decision:
    outcome: Literal["allow", "ask", "deny"]
    tier: Literal["FORBIDDEN", "HIGH", "MEDIUM", "LOW"]
    reason: str
    scope_options: Optional[List[str]] = None
    args_preview: str = ""
    expires_in_s: Union[int, float] = 120
    decided_by: str = "policy"


def load_policy_config() -> Dict[str, Any]:
    """Loads policy.json from the package directory."""
    policy_path = Path(__file__).parent / "policy.json"
    if not policy_path.exists():
        raise FileNotFoundError(f"Permission policy configuration not found: {policy_path}")
    with open(policy_path, "r", encoding="utf-8") as f:
        return json.load(f)


class PolicyEngine:
    """
    Evaluates permission requests deterministically against policy.json rules.
    Maintains per-run usage budgets and active run-scoped grants.
    """

    def __init__(self, policy_data: Optional[Dict[str, Any]] = None):
        self.policy: Dict[str, Any] = policy_data or load_policy_config()
        self.known_tools: Set[str] = set(self.policy.get("known_tools", []))
        self.budgets: Dict[str, Any] = self.policy.get("budgets", {})
        
        # Per-run state: run_id -> set of granted tool keys
        self._run_grants: Dict[str, Set[str]] = {}
        # Per-run usage tracking: run_id -> metric -> count
        self._usage: Dict[str, Dict[str, Any]] = {}
        # Known domains contacted per run
        self._seen_domains: Dict[str, Set[str]] = {}

    def get_permission_mode(self) -> str:
        """
        Returns SWARM_PERMISSION_MODE=strict|demo (default: strict).
        Note: demo only auto-approves MEDIUM tier. FORBIDDEN is NEVER bypassed.
        """
        mode = os.environ.get("SWARM_PERMISSION_MODE", "strict").strip().lower()
        if mode == "demo":
            return "demo"
        return "strict"

    def register_run_grant(self, run_id: str, tool: str, pattern: Optional[str] = None, tier: str = "MEDIUM") -> bool:
        """
        Stores a run-level grant for a MEDIUM-tier tool.
        HIGH tier grants are strictly rejected.
        """
        if tier == "HIGH" or tier == "FORBIDDEN":
            return False  # Run-level grant never allowed for HIGH or FORBIDDEN

        if run_id not in self._run_grants:
            self._run_grants[run_id] = set()

        grant_key = f"{tool}:{pattern}" if pattern else tool
        self._run_grants[run_id].add(grant_key)
        return True

    def has_run_grant(self, run_id: str, tool: str, pattern: Optional[str] = None) -> bool:
        """Checks if a run-level grant exists."""
        grants = self._run_grants.get(run_id, set())
        grant_key = f"{tool}:{pattern}" if pattern else tool
        return tool in grants or grant_key in grants

    def _get_usage(self, run_id: str) -> Dict[str, Any]:
        if run_id not in self._usage:
            self._usage[run_id] = {
                "total_tool_calls": 0,
                "per_tool": {},
                "per_agent": {},
                "tinyfish_calls": 0,
                "command_runs": 0,
            }
        return self._usage[run_id]

    def increment_usage(self, run_id: str, agent: str, tool: str) -> None:
        """Increments usage counters upon successful execution or dispatch."""
        u = self._get_usage(run_id)
        u["total_tool_calls"] += 1
        u["per_tool"][tool] = u["per_tool"].get(tool, 0) + 1
        u["per_agent"][agent] = u["per_agent"].get(agent, 0) + 1
        if "tinyfish" in tool:
            u["tinyfish_calls"] += 1
        if tool == "command_run":
            u["command_runs"] += 1

    def reset_run(self, run_id: str) -> None:
        """Clears usage and grants for a run."""
        self._run_grants.pop(run_id, None)
        self._usage.pop(run_id, None)
        self._seen_domains.pop(run_id, None)

    def _check_budget(self, run_id: str, agent: str, tool: str) -> Optional[str]:
        """Returns denial reason if any execution budget is exceeded."""
        u = self._get_usage(run_id)

        max_total = self.budgets.get("max_total_tool_calls", 100)
        if u["total_tool_calls"] >= max_total:
            return f"Run budget exceeded: maximum total tool calls ({max_total}) reached"

        max_agent = self.budgets.get("max_tool_calls_per_agent", 50)
        if u["per_agent"].get(agent, 0) >= max_agent:
            return f"Agent budget exceeded: '{agent}' reached max tool calls ({max_agent})"

        tool_limits = self.budgets.get("max_tool_calls_per_tool", {})
        if tool in tool_limits and u["per_tool"].get(tool, 0) >= tool_limits[tool]:
            return f"Tool budget exceeded: '{tool}' reached max calls ({tool_limits[tool]})"

        if "tinyfish" in tool:
            max_tf = self.budgets.get("max_tinyfish_calls", 30)
            if u["tinyfish_calls"] >= max_tf:
                return f"TinyFish budget exceeded: reached max calls ({max_tf})"

        if tool == "command_run":
            max_cmd = self.budgets.get("max_command_runs", 25)
            if u["command_runs"] >= max_cmd:
                return f"Command runner budget exceeded: reached max command runs ({max_cmd})"

        return None

    def _check_forbidden(self, run_id: str, tool: str, args: Dict[str, Any]) -> Optional[str]:
        """Evaluates strict FORBIDDEN rules."""
        # 1. Path safety and forbidden secret files
        path_arg = args.get("path") or args.get("file") or args.get("target") or args.get("cwd")
        if path_arg:
            path_str = str(path_arg).strip()
            # Check traversal
            parts = Path(path_str).parts
            if ".." in parts:
                return f"Path traversal '..' is FORBIDDEN in '{path_str}'"

            # Check secret pattern
            basename = Path(path_str).name
            for pat in FORBIDDEN_FILE_PATTERNS:
                if pat.match(basename) or pat.match(path_str):
                    return f"Access to secret/credential pattern '{path_str}' is FORBIDDEN"

            # Check protected system paths
            lower_path = path_str.lower().replace("\\", "/")
            for p_dir in PROTECTED_PROJECT_DIRS:
                if lower_path == p_dir or lower_path.startswith(f"{p_dir}/") or f"/{p_dir}/" in lower_path:
                    return f"Access or modification to protected system path '{p_dir}' is FORBIDDEN"

        # 2. Command execution checks
        if tool == "command_run":
            argv = args.get("argv", [])
            if isinstance(argv, str):
                return "Shell string execution is FORBIDDEN (argv must be a list)"
            if not isinstance(argv, (list, tuple)) or not argv:
                return "Empty or invalid argv list is FORBIDDEN"

            binary = str(argv[0]).strip().lower()

            # Privilege elevation check
            priv_cmds = set(self.policy.get("tiers", {}).get("FORBIDDEN", {}).get("privilege_elevation_commands", []))
            if binary in priv_cmds or any(token.lower() in priv_cmds for token in argv):
                return f"Privilege elevation command '{binary}' is FORBIDDEN"

            # Piping downloads into shell check
            cmd_string = " ".join(str(x) for x in argv).lower()
            pipe_patterns = self.policy.get("tiers", {}).get("FORBIDDEN", {}).get("pipe_to_shell_patterns", [])
            for pat in pipe_patterns:
                if re.search(pat, cmd_string):
                    return "Piping downloads directly into a shell is FORBIDDEN"

        # 3. Foreign process killing check
        if tool == "kill_process":
            started_pids = args.get("run_started_pids", [])
            target_pid = args.get("pid")
            if target_pid and target_pid not in started_pids:
                return f"Killing process PID {target_pid} not spawned by this run is FORBIDDEN"

        return None

    def _is_allowlisted_command(self, argv: List[str]) -> bool:
        """Checks if a command matches the MEDIUM allowlisted binaries and subcommands."""
        if not argv:
            return False
        binary = Path(str(argv[0])).name.lower()
        if binary.endswith(".exe"):
            binary = binary[:-4]

        allowlist = self.policy.get("tiers", {}).get("MEDIUM", {}).get("allowlisted_binaries", {})
        if binary not in allowlist:
            return False

        allowed_subcommands = allowlist[binary]
        if not allowed_subcommands:
            return True  # Any subcommand allowed for this binary

        # Check if the invocation starts with any of the allowed subcommand prefixes
        cmd_rest = " ".join(str(x) for x in argv[1:]).lower()
        for allowed in allowed_subcommands:
            if cmd_rest.startswith(allowed.lower()) or cmd_rest == allowed.lower():
                return True

        return False

    def check(
        self,
        run_id: str,
        agent: str,
        tool: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """
        Determines the safety tier and outcome (allow, ask, deny) for a tool call.
        """
        context = context or {}
        args_str = json.dumps(args, default=str)
        redacted_preview = redact(args_str)[:200]
        expires_s = self.budgets.get("default_approval_timeout_s", 120)

        # 1. Unknown tool check
        if tool not in self.known_tools:
            return Decision(
                outcome="deny",
                tier="HIGH",
                reason=f"Unknown or un-registered tool '{tool}' is denied by default.",
                scope_options=None,
                args_preview=redacted_preview,
                expires_in_s=expires_s,
                decided_by="policy",
            )

        # 2. Strict FORBIDDEN checks (No mode can ever override this)
        forbidden_reason = self._check_forbidden(run_id, tool, args)
        if forbidden_reason:
            return Decision(
                outcome="deny",
                tier="FORBIDDEN",
                reason=forbidden_reason,
                scope_options=None,
                args_preview=redacted_preview,
                expires_in_s=expires_s,
                decided_by="policy",
            )

        # 3. Budget checks
        budget_reason = self._check_budget(run_id, agent, tool)
        if budget_reason:
            return Decision(
                outcome="deny",
                tier="HIGH",
                reason=budget_reason,
                scope_options=None,
                args_preview=redacted_preview,
                expires_in_s=expires_s,
                decided_by="budget",
            )

        # 4. Determine base tier
        tier: Literal["FORBIDDEN", "HIGH", "MEDIUM", "LOW"] = "LOW"
        reason = "Tool call allowed by standard policy"

        # Check HIGH tier
        high_tools = set(self.policy.get("tiers", {}).get("HIGH", {}).get("always_ask_tools", []))
        if tool in high_tools:
            tier = "HIGH"
            reason = f"Tool '{tool}' performs high-impact file/git/tunnel mutations"

        elif tool == "command_run":
            argv = args.get("argv", [])
            if self._is_allowlisted_command(argv):
                tier = "MEDIUM"
                reason = f"Allowlisted development command: {' '.join(str(x) for x in argv[:3])}"
            else:
                tier = "HIGH"
                reason = f"Non-allowlisted command: {' '.join(str(x) for x in argv[:3])}"

        elif tool == "tinyfish_browser_task":
            # Browser task on a new domain is MEDIUM; on existing domain LOW
            url = args.get("url", "")
            domain = url.split("//")[-1].split("/")[0].lower() if "//" in url else url.split("/")[0].lower()
            if run_id not in self._seen_domains:
                self._seen_domains[run_id] = set()
            if domain and domain not in self._seen_domains[run_id]:
                tier = "MEDIUM"
                reason = f"TinyFish browser interaction with new domain '{domain}'"
                self._seen_domains[run_id].add(domain)
            else:
                tier = "LOW"
                reason = f"TinyFish browser interaction on verified domain '{domain}'"

        elif tool in ("file_read", "file_write", "tinyfish_search", "tinyfish_fetch", "feed_post", "card_post"):
            tier = "LOW"
            reason = f"Standard workspace operation: {tool}"

        # 5. Escalation Rule:
        # If the action traces back to untrusted web content, raise tier by one.
        if context.get("web_derived", False):
            if tier == "LOW":
                tier = "MEDIUM"
                reason += " [Escalated: action traces to untrusted web content]"
            elif tier == "MEDIUM":
                tier = "HIGH"
                reason += " [Escalated: action traces to untrusted web content]"

        # 6. Resolve outcome based on tier, run grants, and permission mode
        mode = self.get_permission_mode()

        if tier == "FORBIDDEN":
            return Decision(
                outcome="deny",
                tier="FORBIDDEN",
                reason=reason,
                scope_options=None,
                args_preview=redacted_preview,
                expires_in_s=expires_s,
                decided_by="policy",
            )

        if tier == "HIGH":
            # HIGH tier always asks every time (never auto-approved and never granted for run)
            return Decision(
                outcome="ask",
                tier="HIGH",
                reason=reason,
                scope_options=["once"],
                args_preview=redacted_preview,
                expires_in_s=expires_s,
                decided_by="policy",
            )

        if tier == "MEDIUM":
            # Check if user already granted this tool for the whole run
            if self.has_run_grant(run_id, tool):
                return Decision(
                    outcome="allow",
                    tier="MEDIUM",
                    reason=f"{reason} (Covered by active run-level grant)",
                    scope_options=None,
                    args_preview=redacted_preview,
                    expires_in_s=expires_s,
                    decided_by="grant",
                )

            # In demo mode, MEDIUM is auto-approved
            if mode == "demo":
                return Decision(
                    outcome="allow",
                    tier="MEDIUM",
                    reason=f"{reason} (Auto-approved in demo mode)",
                    scope_options=None,
                    args_preview=redacted_preview,
                    expires_in_s=expires_s,
                    decided_by="demo",
                )

            # Strict mode: ask user, offering both 'once' and 'run' scope
            return Decision(
                outcome="ask",
                tier="MEDIUM",
                reason=reason,
                scope_options=["once", "run"],
                args_preview=redacted_preview,
                expires_in_s=expires_s,
                decided_by="policy",
            )

        # LOW tier
        return Decision(
            outcome="allow",
            tier="LOW",
            reason=reason,
            scope_options=None,
            args_preview=redacted_preview,
            expires_in_s=expires_s,
            decided_by="policy",
        )
