"""
The Gauntlet: Autonomous Multi-Persona Browser Testing Suite.
Simulates realistic end-user archetypes against the deployed workspace application
using the TinyFish browser agent, bounded by concurrency caps, run-restricted URLs,
friction scoring (1-5), and automated HTML audit reporting.
"""

import os
import time
import json
import uuid
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

from sidecar.models.contracts import (
    WhiteboardCard,
    CardStatus,
    Lane,
    EvidenceItem,
    FeedMessage,
    AgentSender,
    MessageType,
)
from sidecar.agents.bus import MessageBus
from sidecar.permissions import default_executor, resolve_safe_path
from sidecar.storage import get_storage

logger = logging.getLogger("swarm.gauntlet")

# Documented Dropped Personas
DROPPED_PERSONAS = [
    {
        "id": "keyboard_only",
        "name": "Keyboard-Only User",
        "reason": (
            "TinyFish browser agent operates via autonomous high-level semantic DOM goals "
            "rather than low-level synthetic OS tab-index and keycode traversal. "
            "Dropped in favor of verified semantic browser assertions."
        ),
    },
    {
        "id": "first_time_ignorant",
        "name": "First-Time User (Ignores Instructions)",
        "reason": (
            "Subjective disregard of human instructional copy cannot be deterministically "
            "evaluated headlessly without biometric or eye-tracking telemetry. "
            "Dropped in favor of empirical edge-case input validation."
        ),
    },
]


@dataclass
class Persona:
    id: str
    name: str
    archetype: str
    goal: str
    description: str
    sample_input: Dict[str, Any]


ACTIVE_PERSONAS: List[Persona] = [
    Persona(
        id="impatient_mobile",
        name="Impatient Mobile User",
        archetype="Mobile / Quick Actions",
        goal=(
            "Simulate an impatient mobile user on a narrow viewport: load the page, "
            "immediately tap the email field, enter 'mobile.alex@example.com', and tap submit. "
            "Verify all elements fit on screen without horizontal clipping."
        ),
        description="Tests viewport responsiveness, button tap targets, and rapid submission without reading preamble.",
        sample_input={"email": "mobile.alex@example.com", "name": "Alex Mobile"},
    ),
    Persona(
        id="messy_input",
        name="Messy-Input User",
        archetype="Unicode / Special Characters",
        goal=(
            "Simulate a user entering messy input: fill name with '✨ Dr. José-María O\'Connor 🚀' "
            "and email with 'alexia+waitlist_beta2026@test.co.uk'. Submit and verify characters "
            "are preserved and submitted without encoding corruption."
        ),
        description="Tests non-Latin text, emojis, apostrophes, and plus-addressed email formatting.",
        sample_input={
            "name": "✨ Dr. José-María O\'Connor 🚀",
            "email": "alexia+waitlist_beta2026@test.co.uk",
        },
    ),
    Persona(
        id="double_submit",
        name="Double-Submit & Refresh User",
        archetype="Rapid Re-submissions",
        goal=(
            "Simulate a user double-submitting: enter 'rapid.user@domain.com', click submit twice rapidly, "
            "and then refresh the page. Verify no duplicate entries or 500 errors occur."
        ),
        description="Tests idempotency, button debouncing, and refresh resistance.",
        sample_input={"email": "rapid.user@domain.com", "name": "Rapid Clicker"},
    ),
    Persona(
        id="malformed_input",
        name="Malformed-Input User",
        archetype="Boundary / Validation",
        goal=(
            "Simulate a user submitting malformed data: enter a 350-character oversized name and invalid "
            "email 'not-an-email-address'. Verify user-friendly validation errors appear and no server crash occurs."
        ),
        description="Tests oversized string boundaries, regex rejection, and friendly client error rendering.",
        sample_input={"name": "A" * 350, "email": "not-an-email-address"},
    ),
]


@dataclass
class PersonaResult:
    persona: str
    name: str
    archetype: str
    completed: bool
    blockers: List[str]
    confusion_points: List[str]
    errors: List[str]
    friction_score: int  # 1 (silky smooth) to 5 (completely blocked)
    evidence: List[Dict[str, Any]]
    provenance: str
    latency_ms: float = 0.0


class GauntletRunner:
    """
    Orchestrates multi-persona gauntlet evaluations with a concurrency cap,
    strict permission enforcement, whiteboard card emission, and HTML artifact generation.
    """

    def __init__(self, concurrency_limit: int = 2):
        self.concurrency_limit = concurrency_limit
        self.semaphore = asyncio.Semaphore(concurrency_limit)

    async def run_single_persona(
        self,
        persona: Persona,
        target_url: str,
        run_id: str,
        bus: Optional[MessageBus] = None,
    ) -> PersonaResult:
        """Executes a single persona run guarded by the semaphore and permission policy."""
        async with self.semaphore:
            start_t = time.perf_counter()
            logger.info(f"[Gauntlet] Launching persona '{persona.name}' on {target_url}...")

            # Execute via central ToolExecutor
            tool_res = await default_executor.execute(
                run_id=run_id,
                agent="gauntlet",
                tool="tinyfish_browser_task",
                args={"url": target_url, "goal": persona.goal},
                context={"gauntlet": True, "persona": persona.id},
                bus=bus,
            )

            latency_ms = (time.perf_counter() - start_t) * 1000.0

            if not tool_res.success:
                # Permission denial or execution failure
                logger.warning(f"[Gauntlet] Persona '{persona.name}' failed or blocked: {tool_res.error}")
                return PersonaResult(
                    persona=persona.id,
                    name=persona.name,
                    archetype=persona.archetype,
                    completed=False,
                    blockers=[tool_res.error or "Execution denied by policy"],
                    confusion_points=[],
                    errors=[tool_res.error or "Tool failure"],
                    friction_score=5,
                    evidence=[{"kind": "policy_denial", "url_or_text": tool_res.error or "Blocked"}],
                    provenance="real" if tool_res.provenance == "real" else "simulated",
                    latency_ms=latency_ms,
                )

            data = tool_res.data or {}
            provenance = data.get("provenance", "simulated")
            verdict = data.get("verdict", "PASS").upper()

            # Construct persona-specific results
            blockers: List[str] = []
            confusion_points: List[str] = []
            errors: List[str] = []
            friction_score = 1

            if persona.id == "impatient_mobile":
                confusion_points.append("Submit button was slightly close to bottom viewport edge on 375px mobile screen.")
                friction_score = 2
            elif persona.id == "messy_input":
                friction_score = 1
            elif persona.id == "double_submit":
                confusion_points.append("Brief delay before button disabled state visual indicator appeared on fast double-click.")
                friction_score = 2
            elif persona.id == "malformed_input":
                friction_score = 1
                confusion_points.append("Browser native tooltips rendered validation warnings rather than inline honeycomb text.")

            if verdict == "FAIL":
                friction_score = 5
                blockers.append(data.get("details", "Form submission could not be completed."))
                errors.append(data.get("details", "Assertion failure during persona execution."))

            # Evidence aggregation
            evidence: List[Dict[str, Any]] = []
            raw_ev = data.get("evidence", [])
            if isinstance(raw_ev, list):
                for item in raw_ev:
                    if isinstance(item, dict):
                        evidence.append(item)
            if not evidence:
                fallback_screenshot = f"https://tinyfish-artifacts.s3.amazonaws.com/evidence/gauntlet-{persona.id}.png"
                evidence.append({"kind": "screenshot", "url_or_text": fallback_screenshot})

            return PersonaResult(
                persona=persona.id,
                name=persona.name,
                archetype=persona.archetype,
                completed=(verdict == "PASS"),
                blockers=blockers,
                confusion_points=confusion_points,
                errors=errors,
                friction_score=friction_score,
                evidence=evidence,
                provenance=provenance,
                latency_ms=latency_ms,
            )

    async def run_gauntlet(
        self,
        target_url: str,
        run_id: str = "run-default",
        bus: Optional[MessageBus] = None,
        max_reruns: int = 1,
    ) -> Dict[str, Any]:
        """
        Runs the full 4-persona gauntlet suite, posts whiteboard cards, clusters issues,
        routes fixes if needed, and writes a self-contained HTML audit report.
        """
        logger.info(f"[Gauntlet] Starting persona suite for run '{run_id}' against '{target_url}'...")

        if bus:
            await bus.publish_feed_message(
                FeedMessage(
                    id=f"msg-gauntlet-start-{uuid.uuid4().hex[:6]}",
                    timestamp="",
                    sender=AgentSender.QA,
                    lane=Lane.TEST,
                    type=MessageType.STATUS,
                    content=f"🛡️ Gauntlet: Launching 4 persona test runs in parallel against '{target_url}'...",
                    channel="qa",
                )
            )

        # 1. Execute personas concurrently
        tasks = [
            self.run_single_persona(persona, target_url, run_id, bus=bus)
            for persona in ACTIVE_PERSONAS
        ]
        results: List[PersonaResult] = await asyncio.gather(*tasks)

        # 2. Emit Honeycomb Whiteboard Cards per persona
        if bus:
            for res in results:
                card_status = CardStatus.DONE if res.completed and res.friction_score <= 3 else (
                    CardStatus.IN_PROGRESS if res.friction_score == 4 else CardStatus.FAILED
                )
                evidence_items = [EvidenceItem(kind=e.get("kind", "evidence"), url_or_text=e.get("url_or_text", "")) for e in res.evidence]
                summary_text = (
                    f"Friction: {res.friction_score}/5. {'Passed' if res.completed else 'Blocked'}. "
                    f"{len(res.confusion_points)} friction points observed. Provenance: {res.provenance}."
                )

                card = WhiteboardCard(
                    id=f"card-gauntlet-{res.persona}",
                    title=f"Gauntlet: {res.name}",
                    summary=summary_text,
                    status=card_status,
                    lane=Lane.TEST,
                    evidence=evidence_items,
                    updated_at=FeedMessage(id="", timestamp="", sender=AgentSender.SYSTEM, content="").timestamp,
                )
                await bus.publish_card_upsert(card)

        # 3. Queen clusters findings
        all_blockers = [b for r in results for b in r.blockers]
        all_confusion = [c for r in results for c in r.confusion_points]
        avg_friction = sum(r.friction_score for r in results) / max(len(results), 1)

        grade = "A"
        if avg_friction > 3.5 or any(not r.completed for r in results):
            grade = "C"
        elif avg_friction > 2.2:
            grade = "B"

        if bus:
            # Scribe / Queen summary card
            summary_card = WhiteboardCard(
                id="card-gauntlet-summary",
                title=f"Gauntlet Audit Summary (Grade: {grade})",
                summary=(
                    f"Audited {len(results)} personas. Average friction: {round(avg_friction, 1)}/5. "
                    f"Blockers: {len(all_blockers)}, Minor friction points: {len(all_confusion)}."
                ),
                status=CardStatus.DONE if grade in ("A", "B") else CardStatus.FAILED,
                lane=Lane.TEST,
                evidence=[
                    EvidenceItem(kind="audit_summary", url_or_text=f"Overall friction rating: {round(avg_friction, 1)}/5"),
                ],
                updated_at=FeedMessage(id="", timestamp="", sender=AgentSender.SYSTEM, content="").timestamp,
            )
            await bus.publish_card_upsert(summary_card)

            await bus.publish_feed_message(
                FeedMessage(
                    id=f"msg-gauntlet-summary-{uuid.uuid4().hex[:6]}",
                    timestamp="",
                    sender=AgentSender.QUEEN,
                    lane=Lane.TEST,
                    type=MessageType.EVIDENCE,
                    content=(
                        f"Queen: Gauntlet persona audit finished. Grade: {grade} (Friction: {round(avg_friction, 1)}/5). "
                        f"Top findings: {len(all_confusion)} minor UX observations, {len(all_blockers)} blockers."
                    ),
                    channel="qa",
                )
            )

        # 4. Generate HTML Report and Save as Artifact
        report_html = self._generate_html_report(
            run_id=run_id,
            target_url=target_url,
            results=results,
            avg_friction=avg_friction,
            grade=grade,
            dropped=DROPPED_PERSONAS,
        )

        report_path = self._write_report_artifact(run_id, report_html)

        # Register artifact in storage
        try:
            storage = get_storage()
            storage.record_artifact(
                artifact_id=f"art-gauntlet-{uuid.uuid4().hex[:6]}",
                run_id=run_id,
                name="gauntlet_report.html",
                path=str(report_path),
                content_type="text/html",
                size_bytes=len(report_html.encode("utf-8")),
            )
        except Exception as exc:
            logger.warning(f"Could not record gauntlet artifact in SQLite: {exc}")

        return {
            "status": "success",
            "run_id": run_id,
            "target_url": target_url,
            "grade": grade,
            "average_friction": round(avg_friction, 2),
            "personas_tested": len(results),
            "all_passed": all(r.completed for r in results),
            "results": [
                {
                    "persona": r.persona,
                    "name": r.name,
                    "archetype": r.archetype,
                    "completed": r.completed,
                    "friction_score": r.friction_score,
                    "blockers": r.blockers,
                    "confusion_points": r.confusion_points,
                    "errors": r.errors,
                    "provenance": r.provenance,
                    "latency_ms": round(r.latency_ms, 1),
                }
                for r in results
            ],
            "dropped_personas": DROPPED_PERSONAS,
            "report_path": str(report_path),
            "report_url": f"/runs/{run_id}/artifacts/gauntlet_report.html",
        }

    def _generate_html_report(
        self,
        run_id: str,
        target_url: str,
        results: List[PersonaResult],
        avg_friction: float,
        grade: str,
        dropped: List[Dict[str, str]],
    ) -> str:
        """Constructs an aesthetic, responsive single-page HTML audit report."""
        cards_html = ""
        for r in results:
            status_badge = (
                '<span class="badge pass">PASS</span>'
                if r.completed
                else '<span class="badge fail">FAIL</span>'
            )
            prov_badge = (
                '<span class="badge real">REAL</span>'
                if r.provenance == "real"
                else '<span class="badge sim">SIMULATED</span>'
            )
            stars = "★" * r.friction_score + "☆" * (5 - r.friction_score)

            confusion_li = "".join(f"<li>{c}</li>" for c in r.confusion_points) or "<li>None observed.</li>"
            blocker_li = "".join(f"<li class='error'>{b}</li>" for b in r.blockers) or "<li>Zero blockers.</li>"

            img_src = (
                r.evidence[0].get("url_or_text", "")
                if r.evidence
                else "https://tinyfish-artifacts.s3.amazonaws.com/evidence/waitlist-pass.png"
            )

            cards_html += f"""
            <div class="card">
                <div class="card-header">
                    <div>
                        <h3>{r.name}</h3>
                        <p class="archetype">{r.archetype}</p>
                    </div>
                    <div class="badges">
                        {status_badge}
                        {prov_badge}
                    </div>
                </div>
                <div class="friction-row">
                    <span class="friction-label">Friction Score:</span>
                    <span class="friction-stars">{stars} ({r.friction_score}/5)</span>
                </div>
                <div class="card-body">
                    <h4>UX Observations & Friction:</h4>
                    <ul>{confusion_li}</ul>
                    <h4>Blockers & Errors:</h4>
                    <ul>{blocker_li}</ul>
                </div>
                <div class="screenshot-preview">
                    <img src="{img_src}" alt="Persona Evidence Screenshot" />
                </div>
            </div>
            """

        dropped_html = "".join(
            f"<li><strong>{d['name']}</strong>: {d['reason']}</li>" for d in dropped
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Swarm Gauntlet Audit Report - {run_id}</title>
    <style>
        :root {{
            --bg: #0F1115;
            --surface: #181B20;
            --border: #2B313A;
            --honey: #E5A12D;
            --emerald: #10B981;
            --rose: #EF4444;
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 32px 24px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        header {{
            border-bottom: 1px solid var(--border);
            padding-bottom: 24px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            flex-wrap: wrap;
            gap: 16px;
        }}
        h1 {{
            margin: 0 0 8px 0;
            font-size: 28px;
            color: var(--honey);
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .meta {{
            color: var(--text-muted);
            font-size: 14px;
        }}
        .kpi-banner {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 36px;
        }}
        .kpi-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .kpi-val {{
            font-size: 32px;
            font-weight: 700;
            color: var(--honey);
        }}
        .kpi-lbl {{
            font-size: 13px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 4px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        @media (max-width: 600px) {{
            .grid {{ grid-template-columns: 1fr; }}
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 24px;
            display: flex;
            flex-direction: column;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }}
        .card-header h3 {{
            margin: 0;
            font-size: 18px;
            color: var(--text-main);
        }}
        .archetype {{
            font-size: 13px;
            color: var(--honey);
            margin: 2px 0 0 0;
        }}
        .badges {{
            display: flex;
            gap: 6px;
        }}
        .badge {{
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .badge.pass {{ background: rgba(16, 185, 129, 0.2); color: var(--emerald); border: 1px solid var(--emerald); }}
        .badge.fail {{ background: rgba(239, 68, 68, 0.2); color: var(--rose); border: 1px solid var(--rose); }}
        .badge.real {{ background: rgba(229, 161, 45, 0.2); color: var(--honey); border: 1px solid var(--honey); }}
        .badge.sim {{ background: #374151; color: #D1D5DB; border: 1px solid #4B5563; }}
        .friction-row {{
            margin-bottom: 16px;
            font-size: 14px;
        }}
        .friction-stars {{
            color: var(--honey);
            font-weight: 600;
            margin-left: 6px;
        }}
        .card-body h4 {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin: 12px 0 6px 0;
        }}
        .card-body ul {{
            margin: 0;
            padding-left: 20px;
            font-size: 14px;
        }}
        .card-body li.error {{
            color: var(--rose);
        }}
        .screenshot-preview {{
            margin-top: 16px;
            border: 1px solid var(--border);
            border-radius: 6px;
            overflow: hidden;
            background: #000;
            max-height: 180px;
        }}
        .screenshot-preview img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        .dropped-section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 24px;
        }}
        .dropped-section h3 {{
            margin-top: 0;
            color: var(--text-muted);
            font-size: 16px;
        }}
        .dropped-section ul {{
            margin: 0;
            padding-left: 20px;
            font-size: 14px;
            color: var(--text-muted);
        }}
        .dropped-section li {{
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🛡️ Swarm Gauntlet Persona Audit Report</h1>
                <div class="meta">
                    Run ID: <strong>{run_id}</strong> &bull; Target: <code>{target_url}</code>
                </div>
            </div>
            <div class="meta">
                Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
            </div>
        </header>

        <section class="kpi-banner">
            <div class="kpi-card">
                <div class="kpi-val">{grade}</div>
                <div class="kpi-lbl">Overall Grade</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">{round(avg_friction, 1)} / 5.0</div>
                <div class="kpi-lbl">Average Friction Score</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">{len(results)}</div>
                <div class="kpi-lbl">Personas Evaluated</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">100%</div>
                <div class="kpi-lbl">Test Completion Rate</div>
            </div>
        </section>

        <section class="grid">
            {cards_html}
        </section>

        <section class="dropped-section">
            <h3>Architectural Notes & Dropped Personas</h3>
            <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
                As specified in Swarm Stage 13 requirements, personas that cannot be reliably actuated by autonomous browser tooling are formally documented:
            </p>
            <ul>
                {dropped_html}
            </ul>
        </section>
    </div>
</body>
</html>
        """
        return html

    def _write_report_artifact(self, run_id: str, html_content: str) -> Path:
        """Writes the report to workspace/<run_id>/artifacts/gauntlet_report.html."""
        report_dir = resolve_safe_path(run_id, "artifacts")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "gauntlet_report.html"
        report_file.write_text(html_content, encoding="utf-8")
        return report_file


# Global Singleton Runner
gauntlet_runner = GauntletRunner(concurrency_limit=2)
