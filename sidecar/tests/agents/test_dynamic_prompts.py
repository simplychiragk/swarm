"""
Tests for Dynamic Prompt & Project Generation.
Verifies that Swarm can take ANY arbitrary user/mentor prompt
(e.g. Hackathon registration, Developer Portfolio, Clinic Appointments, AI Video Waitlist)
and generate custom HTML, CSS, JavaScript, and FastAPI endpoints matching the prompt.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from sidecar.models.specs import extract_project_spec, ProjectSpec
from sidecar.agents.worker import WorkerAgent
from sidecar.agents.queen import QueenAgent
from sidecar.agents.bus import MessageBus
from sidecar.models.contracts import Lane
from sidecar.permissions import resolve_safe_path
from sidecar.main import app

client = TestClient(app)


def test_extract_project_spec_archetypes():
    # 1. Hackathon / Event Registration
    spec_hack = extract_project_spec("Build an event registration page for HackIIITD with track selection and food preferences")
    assert "HackIIITD" in spec_hack.project_name
    assert spec_hack.api_endpoint == "/api/register"
    field_ids = {f.id for f in spec_hack.fields}
    assert "name" in field_ids
    assert "email" in field_ids
    assert "track" in field_ids
    assert "food" in field_ids

    # 2. Portfolio / Personal Website
    spec_port = extract_project_spec("Build a portfolio website for a machine learning engineer with a contact form")
    assert "Machine Learning" in spec_port.project_name
    assert spec_port.api_endpoint == "/api/contact"
    port_fields = {f.id for f in spec_port.fields}
    assert "message" in port_fields
    assert len(spec_port.extra_sections) > 0

    # 3. Clinic Appointment
    spec_clinic = extract_project_spec("Build a doctor consultation booking form for a cardiology clinic")
    assert "Clinic" in spec_clinic.project_name or "MedCare" in spec_clinic.project_name
    assert spec_clinic.api_endpoint == "/api/appointment"
    clinic_fields = {f.id for f in spec_clinic.fields}
    assert "department" in clinic_fields

    # 4. Standard / Fallback Waitlist
    spec_wl = extract_project_spec("Build a landing page with a waitlist form")
    assert "Waitlist" in spec_wl.project_name
    assert spec_wl.api_endpoint == "/api/waitlist"


@pytest.mark.asyncio
async def test_worker_generates_custom_project(monkeypatch, tmp_path):
    run_id = f"run-dynamic-{uuid.uuid4().hex[:6]}"
    db_file = tmp_path / "dynamic.db"
    monkeypatch.setenv("SWARM_DB_PATH", str(db_file))

    bus = MessageBus(run_id=run_id)
    fe_worker = WorkerAgent(name="fe_worker", lane=Lane.FE, bus=bus)
    be_worker = WorkerAgent(name="be_worker", lane=Lane.BE, bus=bus)

    # Prompt: HackIIITD Event
    spec = extract_project_spec("Build an event registration page for HackIIITD with track selection and food preferences")

    await fe_worker.execute_task(
        task_id="task-fe-hack",
        title=f"Responsive {spec.project_name}",
        description="Construct custom event registration UI",
        run_id=run_id,
        spec=spec,
    )

    await be_worker.execute_task(
        task_id="task-be-hack",
        title=f"FastAPI {spec.project_name} Backend",
        description="Construct registration endpoint",
        run_id=run_id,
        spec=spec,
    )

    # Verify generated HTML
    html_path = resolve_safe_path(run_id, "index.html", must_exist=True)
    assert html_path.exists()
    html_content = html_path.read_text(encoding="utf-8")
    assert "HackIIITD" in html_content
    assert 'name="track"' in html_content
    assert 'name="food"' in html_content
    assert 'id="submit-btn"' in html_content

    # Verify generated Backend API
    api_path = resolve_safe_path(run_id, "api/main.py", must_exist=True)
    assert api_path.exists()
    api_content = api_path.read_text(encoding="utf-8")
    assert "/api/register" in api_content


def test_dynamic_api_endpoint_submission():
    run_id = f"run-dyn-api-{uuid.uuid4().hex[:6]}"

    # Submit to custom route /api/register
    resp = client.post(
        f"/runs/{run_id}/preview/api/register",
        json={
            "name": "Tanmay Hacker",
            "email": "tanmay@iiitd.ac.in",
            "track": "AI & Autonomous Agents",
            "food": "Vegetarian",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert "Tanmay Hacker" in data["message"]
    assert data["route"] == "register"

    # Submit to custom route /api/contact
    resp2 = client.post(
        f"/runs/{run_id}/preview/api/contact",
        json={
            "name": "Recruiter Alice",
            "email": "alice@venture.co",
            "message": "Let's discuss a senior engineering role.",
        },
    )
    assert resp2.status_code == 201
    assert "Recruiter Alice" in resp2.json()["message"]
