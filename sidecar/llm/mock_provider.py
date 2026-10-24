"""
Mock LLM Provider for offline deterministic operations.
Returns plausible text or structured JSON payloads for Queen, Worker, and Scribe schemas.
"""

import json
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
from .types import LLMResult


def _extract_schema_properties(json_schema: Any) -> Dict[str, Any]:
    if isinstance(json_schema, dict):
        return json_schema.get("properties", {})
    if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
        schema = json_schema.model_json_schema()
        return schema.get("properties", {})
    return {}


def generate_mock_json_response(json_schema: Any, messages: List[Dict[str, str]]) -> str:
    """Generate realistic deterministic JSON based on schema properties and prompt context."""
    props = _extract_schema_properties(json_schema)
    last_user_content = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_content = m.get("content", "")
            break

    # 1. Queen Planning Schema (contains "tasks")
    if "tasks" in props:
        return json.dumps({
            "tasks": [
                {
                    "id": "task-be-api",
                    "lane": "BE",
                    "title": "FastAPI Waitlist Submission Endpoint",
                    "description": "Construct POST /api/waitlist route with Pydantic email validator and storage",
                    "dependencies": [],
                },
                {
                    "id": "task-fe-hero",
                    "lane": "FE",
                    "title": "Responsive Waitlist Hero Section",
                    "description": "Build modern dark UI with honeycomb styling, name/email/role inputs, and live validation",
                    "dependencies": ["task-be-api"],
                },
                {
                    "id": "task-qa-verify",
                    "lane": "Test",
                    "title": "Browser QA Validation via TinyFish",
                    "description": "Automate end-to-end form fill and submit verification using browser session",
                    "dependencies": ["task-fe-hero"],
                },
                {
                    "id": "task-ops-deploy",
                    "lane": "Ops",
                    "title": "Production Release Gating",
                    "description": "Gate deployment behind human approval check",
                    "dependencies": ["task-qa-verify"],
                },
            ]
        })

    # 2. Queen Interview Schema (contains "question" or "is_finished")
    if "question" in props or "is_finished" in props:
        # If user answered details, conclude interview
        if any(k in last_user_content.lower() for k in ["dark", "indie", "developer", "email", "form", "honeycomb", "landing"]):
            return json.dumps({
                "is_finished": True,
                "question": "",
                "summary": "Audience: indie developers; Theme: dark honeycomb; Fields: name, work email, primary role.",
            })
        return json.dumps({
            "is_finished": False,
            "question": "What visual theme and specific form fields should we prioritize for your waitlist?",
            "summary": "Initial requirement inquiry initiated.",
        })

    # 3. Scribe Whiteboard Card Summary Schema (contains "title" and "summary")
    if "title" in props and "summary" in props and "lane" in props:
        return json.dumps({
            "title": "Agent Coordination Milestone",
            "summary": "Frontend and Backend workers integrated the waitlist endpoint and verified responsive layout.",
            "status": "in_progress",
            "lane": "FE",
        })

    # 4. Worker Deliverable Schema (contains "technical_spec" or "code_files")
    if "technical_spec" in props or "code_files" in props:
        return json.dumps({
            "message": "Constructed responsive waitlist form and verified schema validation.",
            "technical_spec": "POST /api/waitlist accepts {name, email, role} and returns 201 Created.",
            "code_files": [
                {"path": "src/App.tsx", "description": "Hero section waitlist form"},
                {"path": "api/main.py", "description": "FastAPI submission endpoint"}
            ]
        })

    # 5. Chat Reply Schema (contains "intent" and "requires_response")
    if "intent" in props and "requires_response" in props:
        return json.dumps({
            "intent": "proposal",
            "to": "fe_worker",
            "content": "Proposed API schema: POST /api/waitlist with JSON body {name, email, role}. Returns HTTP 201.",
            "requires_response": True,
            "done_with_thread": False
        })

    # 6. QA Evaluation Schema (contains "passed" and "steps")
    if "passed" in props and "steps" in props:
        return json.dumps({
            "passed": True,
            "steps": [
                "1. Loaded landing page at http://localhost:5173",
                "2. Populated work email field with 'test@iiitd.ac.in'",
                "3. Clicked 'Request Access' button",
                "4. Verified HTTP 201 Created and confirmed toast banner appeared"
            ],
            "errors": [],
            "notes": "End-to-end form verification passed with zero DOM errors."
        })

    # 7. Steering Plan Diff Schema (contains "added", "removed", "changed", "kept")
    if "added" in props and "kept" in props and "summary" in props:
        return json.dumps({
            "added": ["Add student ID and university fields to waitlist schema"],
            "removed": [],
            "changed": ["Update form hero component to support student tier badge"],
            "kept": ["FastAPI endpoint infrastructure", "Honeycomb whiteboard Scribe monitoring"],
            "summary": "Incorporated student audience steering into active worker plan."
        })

    # 8. Fallback generic JSON constructed from properties
    fallback = {}
    for key, spec in props.items():
        prop_type = spec.get("type", "string")
        if prop_type == "string":
            fallback[key] = f"Mock {key} value"
        elif prop_type == "array":
            fallback[key] = []
        elif prop_type == "boolean":
            fallback[key] = True
        elif prop_type in ("integer", "number"):
            fallback[key] = 1
        elif prop_type == "object":
            fallback[key] = {}
        else:
            fallback[key] = None

    return json.dumps(fallback)


def generate_mock_text_response(messages: List[Dict[str, str]]) -> str:
    """Generate realistic plain-text completions for agent dialogue."""
    combined = " ".join(m.get("content", "") for m in messages).lower()

    if "queen" in combined:
        return "Queen: I have reviewed the plan. Workers, proceed with parallel construction of the API and UI."
    if "backend" in combined or "be" in combined:
        return "BE Worker: POST /api/waitlist endpoint schema locked. Accepts name, email, and role."
    if "frontend" in combined or "fe" in combined:
        return "FE Worker: Hero section component rendered with Tailwind CSS dark honeycomb styling."
    if "qa" in combined or "test" in combined:
        return "QA Bee: Simulated browser form submission executed successfully. Assertion passed."

    return "Swarm agent processing task successfully according to specification."


def mock_complete(
    messages: List[Dict[str, str]],
    *,
    tier: str = "fast",
    json_schema: Optional[Any] = None,
) -> LLMResult:
    """Executes deterministic mock completion."""
    if json_schema is not None:
        text = generate_mock_json_response(json_schema, messages)
        parsed = json.loads(text)
    else:
        text = generate_mock_text_response(messages)
        parsed = None

    return LLMResult(
        text=text,
        parsed=parsed,
        provider="mock",
        model=f"mock-{tier}-v1",
        latency_ms=15.0,
    )
