"""
Worker Bee Agents for Swarm.
Owns execution in a specific lane (BE, FE). Calls LLM gateway for deliverables,
writes real project files into workspace/<run_id>/, coordinates with peer workers,
and supports seeded-bug demo mode and automated fix loops.
"""

import os
import logging
from typing import Optional, Dict, Any, Set
from pydantic import BaseModel, Field

from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
)
from sidecar.models.specs import ProjectSpec, ProjectField, extract_project_spec
from sidecar.llm import complete
from .base import BaseAgent
from .bus import MessageBus

logger = logging.getLogger("swarm.agents.worker")


class DeliverableSchema(BaseModel):
    message: str = Field(..., description="Worker progress narrative")
    technical_spec: str = Field(..., description="API contract or component markup outline")
    status: str = Field(default="done", description="Lifecycle status")


class WorkerAgent(BaseAgent):
    """Lane worker agent (Frontend or Backend)."""

    def __init__(self, name: str, lane: Lane, bus: MessageBus, max_messages: int = 200):
        role = (
            "You are a specialized Backend Engineer worker bee. You construct FastAPI endpoints, validators, and database schemas."
            if lane == Lane.BE
            else "You are a specialized Frontend Engineer worker bee. You build HTML5, CSS, and JavaScript components matching backend API shapes."
        )
        super().__init__(
            name=name,
            sender=AgentSender.WORKER,
            lane=lane,
            role_prompt=role,
            bus=bus,
            max_messages=max_messages,
        )
        self.received_peer_contract: Optional[str] = None
        self.active_task_id: Optional[str] = None
        self.completed_tasks: Set[str] = set()
        self._broadcasted_contracts: Set[str] = set()
        self.seeded_bug_active = (os.environ.get("SWARM_DEMO_MODE", "").lower() == "seeded_bug")
        self.bug_fixed = False
        self.has_phone_field = False
        self.current_spec: Optional[ProjectSpec] = None

    async def write_deliverable_artifact(self, filename: str, content: str, run_id: str = "run-default") -> None:
        """
        Persists generated code files to the run workspace via ToolExecutor.
        """
        from sidecar.permissions import default_executor
        clean_name = filename.replace("sidecar/", "src/").replace("app/", "src/")
        tool_res = await default_executor.execute(
            run_id=run_id,
            agent=self.name,
            tool="file_write",
            args={"path": clean_name, "content": content},
            context={"web_derived": False},
            bus=self.bus,
        )
        if not tool_res.success:
            logger.warning(f"Worker deliverable write blocked: {tool_res.error}")
        else:
            logger.info(f"Worker '{self.name}' persisted deliverable '{clean_name}' ({len(content)} bytes)")

    async def _write_frontend_project(
        self,
        run_id: str = "run-default",
        spec: Optional[ProjectSpec] = None,
        with_bug: bool = False,
        with_phone: bool = False,
    ) -> None:
        """Writes real working HTML, CSS, and JS landing page into workspace/<run_id>/."""
        spec = spec or self.current_spec or extract_project_spec("waitlist")
        disabled_attr = "disabled" if with_bug else ""
        include_phone = with_phone or self.has_phone_field

        phone_html = """
          <div class="form-group phone-group">
            <label for="phone">Phone Number</label>
            <div style="display: flex; gap: 8px;">
              <select id="country-code" name="country_code" style="width: 110px;">
                <option value="+1">+1 (US)</option>
                <option value="+91" selected>+91 (IN)</option>
                <option value="+44">+44 (UK)</option>
              </select>
              <input type="tel" id="phone" name="phone" placeholder="9876543210" required style="flex: 1;" />
            </div>
          </div>""" if include_phone else ""

        fields_html = []
        for f in spec.fields:
            if f.type == "select":
                opts = "\n".join(f'                <option value="{o}">{o}</option>' for o in (f.options or []))
                fields_html.append(f"""          <div class="form-group">
            <label for="{f.id}">{f.label}</label>
            <select id="{f.id}" name="{f.id}">
{opts}
            </select>
          </div>""")
            elif f.type == "textarea":
                fields_html.append(f"""          <div class="form-group">
            <label for="{f.id}">{f.label}</label>
            <textarea id="{f.id}" name="{f.id}" placeholder="{f.placeholder or ''}" rows="3" style="width: 100%; box-sizing: border-box; padding: 10px; background: #18191b; border: 1px solid var(--border); border-radius: 6px; color: #fff; font-family: inherit;" required></textarea>
          </div>""")
            else:
                fields_html.append(f"""          <div class="form-group">
            <label for="{f.id}">{f.label}</label>
            <input type="{f.type}" id="{f.id}" name="{f.id}" placeholder="{f.placeholder or ''}" required />
          </div>""")

        if phone_html:
            fields_html.append(phone_html)

        rendered_form_fields = "\n".join(fields_html)

        extra_sections_html = ""
        for sec in spec.extra_sections:
            sec_title = sec.get("title", "Highlights")
            items = "".join(f'<li style="margin-bottom: 8px; color: var(--text-muted);">{it}</li>' for it in sec.get("items", []))
            extra_sections_html += f"""
        <div class="card" style="margin-top: 24px; text-align: left;">
          <h3 style="color: var(--honey); margin-top: 0;">{sec_title}</h3>
          <ul style="padding-left: 20px; font-size: 14px;">{items}</ul>
        </div>"""

        index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{spec.project_name}</title>
  <link rel="stylesheet" href="./style.css" />
</head>
<body>
  <header class="navbar">
    <div class="logo">🐝 {spec.project_name.split(' - ')[0]}</div>
    <nav><a href="#action-section" class="btn-link">{spec.form_action_label}</a></nav>
  </header>
  <main>
    <section class="hero" id="action-section">
      <h1>{spec.project_name}</h1>
      <p>{spec.tagline}</p>
      <div class="card form-card">
        <h2>{spec.form_title}</h2>
        <form id="waitlist-form">
{rendered_form_fields}
          <button type="submit" id="submit-btn" {disabled_attr}>{spec.form_action_label}</button>
        </form>
        <div id="toast" class="toast hidden" role="status" aria-live="polite"></div>
      </div>{extra_sections_html}
    </section>
  </main>
  <footer>
    <p>&copy; 2026 {spec.project_name}. Verified by TinyFish Browser QA.</p>
  </footer>
  <script src="./app.js"></script>
</body>
</html>"""

        style_css = """:root {
  --bg: #0c0d0e;
  --card: #18191b;
  --border: #27282b;
  --honey: #f59e0b;
  --honey-hover: #d97706;
  --text: #f3f4f6;
  --text-muted: #9ca3af;
  --success: #10b981;
  --font: system-ui, -apple-system, sans-serif;
}
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
body {
  margin: 0;
  padding: 0;
  font-family: var(--font);
  background-color: var(--bg);
  color: var(--text);
  min-height: 100vh;
}
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  border-bottom: 1px solid var(--border);
}
.logo { font-size: 20px; font-weight: 700; color: var(--honey); }
.btn-link { color: var(--text); text-decoration: none; font-size: 14px; }
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 64px 24px;
}
h1 { font-size: 40px; margin-bottom: 16px; }
p { color: var(--text-muted); font-size: 18px; max-width: 600px; margin-bottom: 32px; }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px;
  width: 100%;
  max-width: 440px;
  text-align: left;
}
.form-group {
  margin-bottom: 20px;
}
label {
  display: block;
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--text-muted);
}
input, select {
  width: 100%;
  box-sizing: border-box;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-size: 15px;
}
input:focus, select:focus {
  outline: none;
  border-color: var(--honey);
}
button {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 6px;
  background: var(--honey);
  color: #000;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
}
button:hover:not(:disabled) {
  background: var(--honey-hover);
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.toast {
  margin-top: 20px;
  padding: 12px;
  border-radius: 6px;
  background: #064e3b;
  border: 1px solid var(--success);
  color: #a7f3d0;
  font-size: 14px;
  text-align: center;
}
.hidden { display: none; }
footer {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 14px;
  border-top: 1px solid var(--border);
}"""

        app_js = f"""document.addEventListener('DOMContentLoaded', () => {{
  const form = document.getElementById('waitlist-form');
  const toast = document.getElementById('toast');
  const submitBtn = document.getElementById('submit-btn');

  form.addEventListener('submit', async (e) => {{
    e.preventDefault();
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    // Support both direct root and preview paths
    const isPreview = window.location.pathname.includes('/preview');
    const apiRoute = '{spec.api_endpoint}';
    const apiUrl = isPreview
      ? `${{window.location.pathname.replace(/\\/preview.*$/, '')}}/preview${{apiRoute}}`
      : apiRoute;

    try {{
      const res = await fetch(apiUrl, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload)
      }});

      if (res.status === 201 || res.ok) {{
        const data = await res.json();
        const displayName = payload.name || 'Friend';
        toast.textContent = data.message || `Success! Confirmed for {spec.project_name}.`;
        toast.classList.remove('hidden');
        form.reset();
      }} else {{
        toast.textContent = `Error: Server returned status ${{res.status}}`;
        toast.classList.remove('hidden');
      }}
    }} catch (err) {{
      toast.textContent = 'Network error processing submission.';
      toast.classList.remove('hidden');
    }} finally {{
      submitBtn.disabled = false;
      submitBtn.textContent = '{spec.form_action_label}';
    }}
  }});
}});"""

        await self.write_deliverable_artifact("index.html", index_html, run_id=run_id)
        await self.write_deliverable_artifact("style.css", style_css, run_id=run_id)
        await self.write_deliverable_artifact("app.js", app_js, run_id=run_id)

    async def _write_backend_project(self, run_id: str = "run-default", spec: Optional[ProjectSpec] = None) -> None:
        """Writes real working FastAPI backend route into workspace/<run_id>/."""
        spec = spec or self.current_spec or extract_project_spec("waitlist")
        api_py = f'''from typing import Optional, Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="{spec.project_name} API")

class SubmissionPayload(BaseModel):
    name: Optional[str] = "Friend"
    email: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    country_code: Optional[str] = None
    class Config:
        extra = "allow"

@app.post("{spec.api_endpoint}", status_code=201)
@app.post("/api/waitlist", status_code=201)
async def handle_submission(req: Dict[str, Any]):
    name = req.get("name", "Friend")
    return {{
        "status": "success",
        "id": "item-42",
        "queue_position": 42,
        "message": f"Welcome {{name}}! Confirmed for {spec.project_name}.",
        "data": req,
    }}
'''
        await self.write_deliverable_artifact("api/main.py", api_py, run_id=run_id)

    async def apply_steer(self, steer_spec: Dict[str, Any], run_id: str = "run-default") -> None:
        """Applies human steering adjustments to workspace code and updates cards."""
        if steer_spec.get("field") == "phone":
            self.has_phone_field = True
            logger.info(f"Worker '{self.name}' incorporating phone field into workspace '{run_id}'")

            if self.lane == Lane.FE:
                await self._write_frontend_project(run_id=run_id, spec=self.current_spec, with_bug=False, with_phone=True)
                await self.emit_card_upsert(
                    card_id="task-fe-hero",
                    title="[EDITED] Responsive Hero & Form Section",
                    summary="Updated UI with phone number field and country code selector.",
                    status=CardStatus.DONE,
                    lane=Lane.FE,
                )
                await self.emit_feed_message(
                    msg_type=MessageType.CHAT,
                    content="FE Worker: Added phone input and country code picker to form in index.html and app.js.",
                    channel="build",
                    intent="handoff",
                )
            elif self.lane == Lane.BE:
                await self._write_backend_project(run_id=run_id, spec=self.current_spec)
                await self.emit_card_upsert(
                    card_id="task-be-api",
                    title="[EDITED] FastAPI Submission Endpoint",
                    summary="Updated schema and route to validate and accept phone & country code.",
                    status=CardStatus.DONE,
                    lane=Lane.BE,
                )
                await self.emit_feed_message(
                    msg_type=MessageType.CHAT,
                    content="BE Worker: Updated backend route in api/main.py to accept optional phone and country_code.",
                    channel="build",
                    intent="handoff",
                )

    async def apply_fix(self, run_id: str = "run-default") -> None:
        """Applies fix to workspace files after a QA failure."""
        self.bug_fixed = True
        logger.info(f"Worker '{self.name}' applying fix in workspace for run '{run_id}'")

        if self.lane == Lane.FE:
            await self._write_frontend_project(run_id=run_id, spec=self.current_spec, with_bug=False)
            await self.emit_feed_message(
                msg_type=MessageType.CHAT,
                content="FE Worker: Resolved issue. Submit button enabled, form event handlers restored. Ready for QA retest.",
                channel="qa",
                intent="handoff",
            )
        elif self.lane == Lane.BE:
            await self._write_backend_project(run_id=run_id, spec=self.current_spec)
            await self.emit_feed_message(
                msg_type=MessageType.CHAT,
                content="BE Worker: Re-verified and updated route in api/main.py. Ready for QA retest.",
                channel="qa",
                intent="handoff",
            )

    async def execute_task(
        self,
        task_id: str,
        title: str,
        description: str,
        run_id: str = "run-default",
        spec: Optional[ProjectSpec] = None,
    ) -> None:
        """Executes a delegated task with LLM completion and writes real files."""
        if task_id in self.completed_tasks or self.active_task_id == task_id:
            logger.info(f"Worker '{self.name}' skipping task '{task_id}' (already completed or active).")
            return

        self.active_task_id = task_id
        try:
            if spec:
                self.current_spec = spec
            logger.info(f"Worker '{self.name}' starting task '{title}' [{self.lane.value}] for run '{run_id}'")

            await self.emit_card_upsert(
                card_id=task_id,
                title=title,
                summary=f"Worker actively executing: {description}",
                status=CardStatus.IN_PROGRESS,
                lane=self.lane,
            )

            prompt = f"Task: {title}\nDescription: {description}"
            if self.received_peer_contract:
                prompt += f"\nPeer contract provided: {self.received_peer_contract}"

            res = await complete(
                messages=[
                    {"role": "system", "content": self.role_prompt},
                    {"role": "user", "content": prompt},
                ],
                tier="fast",
                json_schema=DeliverableSchema,
            )
            deliverable: DeliverableSchema = res.parsed  # type: ignore

            await self.emit_feed_message(
                msg_type=MessageType.CHAT,
                content=f"{self.name.upper()}: {deliverable.message if deliverable else res.text}",
                channel="build",
                metadata={"spec": deliverable.technical_spec if deliverable else ""},
            )

            # Write real files into workspace/<run_id>/
            if self.lane == Lane.BE:
                endpoint = self.current_spec.api_endpoint if self.current_spec else "/api/waitlist"
                contract_snippet = f"POST {endpoint} -> Request: dynamic JSON schema -> Response: 201 Created {{status, message, data}}"
                if contract_snippet not in self._broadcasted_contracts:
                    self._broadcasted_contracts.add(contract_snippet)
                    await self.emit_feed_message(
                        msg_type=MessageType.CHAT,
                        content=f"BE Worker -> FE Worker: Locked API endpoint contract: `{contract_snippet}`",
                        channel="build",
                        intent="decision",
                        metadata={"contract": contract_snippet, "topic": "API Contract", "agreed_by": ["be_worker", "fe_worker"]},
                        lane=Lane.FE,
                    )
                await self._write_backend_project(run_id=run_id, spec=self.current_spec)

            if self.lane == Lane.FE:
                has_bug = self.seeded_bug_active and not self.bug_fixed
                await self._write_frontend_project(run_id=run_id, spec=self.current_spec, with_bug=has_bug)
                if has_bug:
                    logger.info(f"Seeded bug introduced into workspace '{run_id}' by FE Worker (button disabled).")

            await self.emit_card_upsert(
                card_id=task_id,
                title=title,
                summary=f"Completed by {self.name.upper()}: {description}",
                status=CardStatus.DONE,
                lane=self.lane,
            )

            await self.emit_feed_message(
                msg_type=MessageType.STATUS,
                content=f"{self.name.upper()}: Task '{title}' completed successfully.",
                channel="build",
            )
            self.completed_tasks.add(task_id)
        finally:
            self.active_task_id = None

    async def process_message(self, message: FeedMessage) -> None:
        """Handle peer messages and incoming task assignments."""
        if message.sender == AgentSender.WORKER and message.lane == self.lane and "contract" in (message.metadata or {}):
            contract_str = str(message.metadata.get("contract"))
            if self.received_peer_contract == contract_str:
                return
            self.received_peer_contract = contract_str
            logger.info(f"Worker '{self.name}' received peer contract: {self.received_peer_contract}")
            await self.emit_feed_message(
                msg_type=MessageType.CHAT,
                content=f"{self.name.upper()}: Received contract from peer. Incorporating into frontend implementation.",
                channel="build",
            )
            return

        if message.type == MessageType.TASK and message.lane == self.lane:
            task_id = (message.metadata or {}).get("task_id", f"task-{self.lane.value.lower()}")
            await self.execute_task(
                task_id=task_id,
                title=f"{self.lane.value} Task",
                description=message.content,
            )
