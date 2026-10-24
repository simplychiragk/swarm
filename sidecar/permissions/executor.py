"""
Central Tool Executor for Swarm Permissions.
Every tool invocation must pass through this executor.
Deterministic policy checks gate execution. Unapproved tools are suspended,
timed out, or denied. All outputs and audit logs are redacted.
"""

import os
import time
import uuid
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from ..models.contracts import (
    ApprovalRequest,
    ApprovalResponse,
    FeedMessage,
    WhiteboardCard,
    CardStatus,
    AgentSender,
    Lane,
    MessageType,
    EvidenceItem,
)
from .policy import PolicyEngine, Decision
from .path_safety import resolve_safe_path, get_run_workspace
from .command_runner import run_safe_command, CommandResult
from .redaction import redact, redact_data
from .audit import record_permission_event


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    tier: str = "LOW"
    outcome: str = "allow"
    tool: str = ""


class ApprovalCoordinator:
    """Coordinates suspended async approval requests awaiting user response."""

    def __init__(self):
        self._pending_approvals: Dict[str, asyncio.Future[ApprovalResponse]] = {}

    def register(self, approval_id: str) -> asyncio.Future[ApprovalResponse]:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[ApprovalResponse] = loop.create_future()
        self._pending_approvals[approval_id] = fut
        return fut

    def resolve(self, approval_id: str, response: ApprovalResponse) -> bool:
        fut = self._pending_approvals.pop(approval_id, None)
        if fut and not fut.done():
            fut.set_result(response)
            return True
        return False

    def cancel_all(self):
        for approval_id, fut in list(self._pending_approvals.items()):
            if not fut.done():
                fut.cancel()
        self._pending_approvals.clear()


# Global singleton coordinator
approval_coordinator = ApprovalCoordinator()


async def _bus_publish_feed(
    bus: Any,
    sender: AgentSender,
    content: str,
    lane: Lane = Lane.OPS,
    msg_type: MessageType = MessageType.STATUS,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    now_ts = datetime.now(timezone.utc).isoformat()
    msg = FeedMessage(
        id=f"msg-guard-{uuid.uuid4().hex[:6]}",
        timestamp=now_ts,
        sender=sender,
        lane=lane,
        type=msg_type,
        content=content,
        metadata=metadata,
    )
    if hasattr(bus, "publish_feed_message"):
        await bus.publish_feed_message(msg)
    elif hasattr(bus, "emit_feed_message"):
        await bus.emit_feed_message(msg_type=msg_type, content=content, metadata=metadata, lane=lane)


async def _bus_publish_card(bus: Any, card: WhiteboardCard) -> None:
    if hasattr(bus, "publish_card_upsert"):
        await bus.publish_card_upsert(card)
    elif hasattr(bus, "emit_card_upsert"):
        await bus.emit_card_upsert(
            card_id=card.id,
            title=card.title,
            summary=card.summary,
            status=card.status,
            lane=card.lane,
            evidence=card.evidence,
        )


async def _bus_publish_approval(bus: Any, req: ApprovalRequest) -> None:
    if hasattr(bus, "publish_approval_request"):
        await bus.publish_approval_request(req)
    elif hasattr(bus, "emit_approval_request"):
        await bus.emit_approval_request(request=req)


class ToolExecutor:
    """
    The singular execution gateway for all agent tool invocations.
    Guarantees deterministic PolicyEngine evaluation, secret redaction,
    SQLite audit trail recording, and asynchronous approval gating.
    """

    def __init__(self, policy_engine: Optional[PolicyEngine] = None):
        self.policy_engine = policy_engine or PolicyEngine()
        self._tool_records: Dict[str, List[Dict[str, Any]]] = {}

    def get_tool_records(self, run_id: str) -> List[Dict[str, Any]]:
        """Returns the in-memory log of all tool executions for a given run."""
        return list(self._tool_records.get(run_id, []))

    def _record_tool_run(
        self,
        run_id: str,
        agent: str,
        tool: str,
        args_summary: str,
        tier: str,
        outcome: str,
        latency_ms: float,
        provenance: str,
        error: Optional[str] = None,
    ) -> None:
        if run_id not in self._tool_records:
            self._tool_records[run_id] = []
        self._tool_records[run_id].append({
            "tool": tool,
            "agent": agent,
            "args_summary": args_summary,
            "tier": tier,
            "outcome": outcome,
            "latency_ms": latency_ms,
            "provenance": provenance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
        })

    async def execute(
        self,
        run_id: str,
        agent: str,
        tool: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        bus: Optional[Any] = None,
    ) -> ToolResult:
        """
        Executes a tool with strict permission evaluation and approval gating.
        """
        start_time = time.perf_counter()
        context = context or {}
        # 1. Deterministic Policy Check
        decision: Decision = self.policy_engine.check(
            run_id=run_id,
            agent=agent,
            tool=tool,
            args=args,
            context=context,
        )

        args_summary = redact(str(args))[:250]

        # 2. Handle DENY (FORBIDDEN, budget exhaustion, or unknown tool)
        if decision.outcome == "deny":
            record_permission_event(
                run_id=run_id,
                agent=agent,
                tool=tool,
                args_summary=args_summary,
                tier=decision.tier,
                outcome="deny",
                decided_by=decision.decided_by,
                reason=decision.reason,
            )
            lat_ms = round((time.perf_counter() - start_time) * 1000, 1)
            self._record_tool_run(run_id, agent, tool, args_summary, decision.tier, "deny", lat_ms, "real", error=decision.reason)

            if bus:
                await self._emit_deny_events(bus, agent, tool, decision)

            return ToolResult(
                success=False,
                error=f"Permission Denied: {decision.reason}",
                tier=decision.tier,
                outcome="deny",
                tool=tool,
            )

        # 3. Handle ASK (HIGH tier or ungranted MEDIUM tier)
        if decision.outcome == "ask":
            record_permission_event(
                run_id=run_id,
                agent=agent,
                tool=tool,
                args_summary=args_summary,
                tier=decision.tier,
                outcome="ask",
                decided_by="policy",
                reason=decision.reason,
            )

            approval_id = f"appr-{uuid.uuid4().hex[:8]}"
            card_id = f"card-guard-{tool}-{uuid.uuid4().hex[:4]}"

            appr_request = ApprovalRequest(
                id=approval_id,
                card_id=card_id,
                prompt=f"Agent '{agent}' requests authorization for tool '{tool}' ({decision.tier} risk). Reason: {decision.reason}",
                options=["Approve Once", "Approve For Run", "Deny"]
                if "run" in (decision.scope_options or [])
                else ["Approve", "Deny"],
                lane=Lane.OPS,
                tool=tool,
                args_preview=decision.args_preview,
                risk="high" if decision.tier == "HIGH" else "medium",
                reason=decision.reason,
                agent=agent,
                scope_options=decision.scope_options,
                expires_in_s=decision.expires_in_s,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            # Emit approval request and feed message to bus if present
            fut = approval_coordinator.register(approval_id)

            if bus:
                await self._emit_ask_events(bus, agent, tool, decision, appr_request)

            try:
                # Suspend execution waiting for human decision or timeout
                user_response: ApprovalResponse = await asyncio.wait_for(
                    fut,
                    timeout=decision.expires_in_s,
                )
            except asyncio.TimeoutError:
                # Default on timeout is strictly DENY
                timeout_reason = f"Approval timed out after {decision.expires_in_s}s. Request DENIED."
                record_permission_event(
                    run_id=run_id,
                    agent=agent,
                    tool=tool,
                    args_summary=args_summary,
                    tier=decision.tier,
                    outcome="deny",
                    decided_by="timeout",
                    reason=timeout_reason,
                )
                lat_ms = round((time.perf_counter() - start_time) * 1000, 1)
                self._record_tool_run(run_id, agent, tool, args_summary, decision.tier, "deny", lat_ms, "real", error=timeout_reason)

                if bus:
                    await self._emit_timeout_events(bus, agent, tool, card_id, timeout_reason)

                return ToolResult(
                    success=False,
                    error=f"Permission Denied: {timeout_reason}",
                    tier=decision.tier,
                    outcome="deny",
                    tool=tool,
                )

            # User responded: check decision and scope
            decision_val = user_response.decision
            scope_val = user_response.scope or ("once" if decision_val == "approve" else "deny")

            if decision_val != "approve" or scope_val == "deny":
                user_denial = user_response.note or "User denied permission request"
                record_permission_event(
                    run_id=run_id,
                    agent=agent,
                    tool=tool,
                    args_summary=args_summary,
                    tier=decision.tier,
                    outcome="deny",
                    decided_by="user",
                    reason=user_denial,
                )
                lat_ms = round((time.perf_counter() - start_time) * 1000, 1)
                self._record_tool_run(run_id, agent, tool, args_summary, decision.tier, "deny", lat_ms, "real", error=user_denial)

                if bus:
                    await self._emit_user_deny_events(bus, agent, tool, card_id, user_denial)

                return ToolResult(
                    success=False,
                    error=f"Permission Denied: {user_denial}",
                    tier=decision.tier,
                    outcome="deny",
                    tool=tool,
                )

            # User approved!
            if scope_val == "run" and decision.tier == "MEDIUM":
                # Register grant for this run
                self.policy_engine.register_run_grant(run_id, tool, tier="MEDIUM")

            record_permission_event(
                run_id=run_id,
                agent=agent,
                tool=tool,
                args_summary=args_summary,
                tier=decision.tier,
                outcome="allow",
                decided_by="user",
                reason=f"Authorized by user (scope: {scope_val})",
            )

            if bus:
                await _bus_publish_feed(
                    bus=bus,
                    sender=AgentSender.SYSTEM,
                    content=f"🛡️ User authorized '{agent}' to execute tool '{tool}' (scope: {scope_val}).",
                    lane=Lane.OPS,
                    msg_type=MessageType.STATUS,
                )

        # 4. Handle ALLOW (auto-allowed LOW, demo MEDIUM, or granted MEDIUM)
        if decision.outcome == "allow":
            record_permission_event(
                run_id=run_id,
                agent=agent,
                tool=tool,
                args_summary=args_summary,
                tier=decision.tier,
                outcome="allow",
                decided_by=decision.decided_by,
                reason=decision.reason,
            )

        # 5. Dispatch Tool
        self.policy_engine.increment_usage(run_id, agent, tool)
        try:
            raw_result = await self._dispatch_tool(run_id, tool, args)
            clean_result = redact_data(raw_result)
            lat_ms = round((time.perf_counter() - start_time) * 1000, 1)

            provenance = "real"
            if isinstance(clean_result, dict) and "provenance" in clean_result:
                provenance = clean_result["provenance"]
            elif tool.startswith("tinyfish_"):
                from ..tools.client import TinyFishClient
                provenance = "real" if TinyFishClient().is_live_configured() else "simulated"

            self._record_tool_run(run_id, agent, tool, args_summary, decision.tier, "allow", lat_ms, provenance)

            return ToolResult(
                success=True,
                data=clean_result,
                tier=decision.tier,
                outcome="allow",
                tool=tool,
            )
        except Exception as exc:
            err_msg = redact(f"Tool '{tool}' execution failed: {exc}")
            lat_ms = round((time.perf_counter() - start_time) * 1000, 1)
            self._record_tool_run(run_id, agent, tool, args_summary, decision.tier, "failed", lat_ms, "real", error=err_msg)
            return ToolResult(
                success=False,
                error=err_msg,
                tier=decision.tier,
                outcome="allow",
                tool=tool,
            )

    async def _dispatch_tool(self, run_id: str, tool: str, args: Dict[str, Any]) -> Any:
        """Dispatches validated tool invocation to its underlying handler."""
        if tool == "file_read":
            target_path = resolve_safe_path(run_id, args["path"], must_exist=True)
            return {"content": target_path.read_text(encoding="utf-8", errors="replace"), "path": str(target_path)}

        elif tool == "file_write":
            target_path = resolve_safe_path(run_id, args["path"], for_write=True)
            content = args.get("content", "")
            target_path.write_text(content, encoding="utf-8")
            return {
                "path": str(target_path.relative_to(get_run_workspace(run_id))),
                "bytes_written": len(content.encode("utf-8")),
            }

        elif tool == "file_delete":
            target_path = resolve_safe_path(run_id, args["path"], must_exist=True)
            if target_path.is_file():
                target_path.unlink()
            elif target_path.is_dir():
                import shutil
                shutil.rmtree(target_path)
            return {"deleted": True, "path": str(target_path)}

        elif tool == "command_run":
            workspace = get_run_workspace(run_id)
            argv = args["argv"]
            timeout = float(args.get("timeout_s", 30.0))
            cmd_result: CommandResult = await run_safe_command(argv, cwd=workspace, timeout_s=timeout)
            return {
                "exit_code": cmd_result.exit_code,
                "stdout": cmd_result.stdout,
                "stderr": cmd_result.stderr,
                "duration_s": cmd_result.duration_s,
                "timed_out": cmd_result.timed_out,
                "truncated": cmd_result.truncated,
            }

        elif tool == "tinyfish_search":
            from ..tools.client import TinyFishClient
            client = TinyFishClient()
            return await client.search(query=args["query"], purpose=args.get("purpose", "research"))

        elif tool == "tinyfish_fetch":
            from ..tools.client import TinyFishClient
            client = TinyFishClient()
            return await client.fetch(url=args["url"])

        elif tool == "tinyfish_browser_task":
            from ..tools.client import TinyFishClient
            client = TinyFishClient()
            return await client.run_browser_task(url=args["url"], goal=args.get("goal", "verify form submission"))

        elif tool in ("feed_post", "card_post", "git_write", "git_push", "tunnel_deploy"):
            # Placeholder tool responses for mock or extensible flows
            return {"status": "ok", "tool": tool, "args": args}

        raise NotImplementedError(f"Handler for tool '{tool}' is not implemented.")

    async def _emit_deny_events(self, bus: Any, agent: str, tool: str, decision: Decision) -> None:
        """Emits compact feed message and whiteboard card guard evidence upon denial."""
        await _bus_publish_feed(
            bus=bus,
            sender=AgentSender.SYSTEM,
            content=f"🛡️ Guard DENIED {agent} calling '{tool}': {decision.reason}",
            lane=Lane.OPS,
            msg_type=MessageType.ERROR,
            metadata={"tool": tool, "tier": decision.tier, "outcome": "deny"},
        )

        card_id = f"card-guard-deny-{uuid.uuid4().hex[:6]}"
        now_ts = datetime.now(timezone.utc).isoformat()
        await _bus_publish_card(
            bus=bus,
            card=WhiteboardCard(
                id=card_id,
                title=f"Security Alert: {tool} Blocked",
                summary=f"Guard blocked {agent} from executing '{tool}'. {decision.reason}",
                status=CardStatus.FAILED,
                lane=Lane.OPS,
                evidence=[
                    EvidenceItem(kind="guard", url_or_text=f"Blocked: {decision.reason}")
                ],
                updated_at=now_ts,
            ),
        )

    async def _emit_ask_events(
        self,
        bus: Any,
        agent: str,
        tool: str,
        decision: Decision,
        appr_request: ApprovalRequest,
    ) -> None:
        """Emits feed notification, approval card, and approval request event."""
        await _bus_publish_feed(
            bus=bus,
            sender=AgentSender.SYSTEM,
            content=f"🛡️ Guard awaiting authorization for {agent} calling '{tool}' ({decision.tier} risk)...",
            lane=Lane.OPS,
            msg_type=MessageType.STATUS,
            metadata={"tool": tool, "tier": decision.tier, "approval_id": appr_request.id},
        )

        now_ts = datetime.now(timezone.utc).isoformat()
        approval_card = WhiteboardCard(
            id=appr_request.card_id,
            title=f"Authorization Required: {tool}",
            summary=f"Agent '{agent}' requests authorization to run '{tool}'. {decision.reason}",
            status=CardStatus.NEEDS_APPROVAL,
            lane=Lane.OPS,
            evidence=[
                EvidenceItem(kind="guard", url_or_text=f"Awaiting authorization ({decision.tier})")
            ],
            updated_at=now_ts,
        )
        appr_request.card = approval_card

        await _bus_publish_card(bus=bus, card=approval_card)
        await _bus_publish_approval(bus=bus, req=appr_request)

    async def _emit_timeout_events(
        self,
        bus: Any,
        agent: str,
        tool: str,
        card_id: str,
        reason: str,
    ) -> None:
        await _bus_publish_feed(
            bus=bus,
            sender=AgentSender.SYSTEM,
            content=f"🛡️ Guard authorization timed out for {agent} calling '{tool}'. Operation DENIED.",
            lane=Lane.OPS,
            msg_type=MessageType.ERROR,
        )
        now_ts = datetime.now(timezone.utc).isoformat()
        await _bus_publish_card(
            bus=bus,
            card=WhiteboardCard(
                id=card_id,
                title=f"Authorization Timed Out: {tool}",
                summary=f"Permission timed out. Operation blocked by policy default.",
                status=CardStatus.FAILED,
                lane=Lane.OPS,
                evidence=[
                    EvidenceItem(kind="guard", url_or_text=reason)
                ],
                updated_at=now_ts,
            ),
        )

    async def _emit_user_deny_events(
        self,
        bus: Any,
        agent: str,
        tool: str,
        card_id: str,
        reason: str,
    ) -> None:
        await _bus_publish_feed(
            bus=bus,
            sender=AgentSender.SYSTEM,
            content=f"🛡️ User DENIED authorization for {agent} to run '{tool}': {reason}",
            lane=Lane.OPS,
            msg_type=MessageType.STATUS,
        )
        now_ts = datetime.now(timezone.utc).isoformat()
        await _bus_publish_card(
            bus=bus,
            card=WhiteboardCard(
                id=card_id,
                title=f"Authorization Denied: {tool}",
                summary=f"User rejected authorization for '{tool}': {reason}",
                status=CardStatus.FAILED,
                lane=Lane.OPS,
                evidence=[
                    EvidenceItem(kind="guard", url_or_text=f"Denied by user: {reason}")
                ],
                updated_at=now_ts,
            ),
        )


# Default singleton instance
default_executor = ToolExecutor()
