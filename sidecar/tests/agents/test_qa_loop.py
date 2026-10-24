"""
Unit tests for Stage 7: QA Bee verification, fail -> fix -> pass loop, and retry limit.
"""

import os
import pytest
from sidecar.agents.bus import MessageBus
from sidecar.agents.queen import QueenAgent
from sidecar.agents.worker import WorkerAgent
from sidecar.tools.agents import QABee
from sidecar.tools.client import TinyFishClient
from sidecar.models.contracts import Lane, CardStatus


@pytest.fixture
def qa_run_id():
    return "test-run-qa-loop-7"


@pytest.mark.asyncio
async def test_qa_bee_passes_clean_landing_page(qa_run_id):
    """Verify QABee passes when landing page has no bugs."""
    old_perm = os.environ.get("SWARM_PERMISSION_MODE")
    os.environ["SWARM_PERMISSION_MODE"] = "demo"

    try:
        bus = MessageBus(run_id=qa_run_id)
        fe_worker = WorkerAgent("fe_worker", Lane.FE, bus)
        # Write clean landing page
        await fe_worker._write_frontend_project(run_id=qa_run_id, with_bug=False)

        qa_bee = QABee(bus, client=TinyFishClient(api_key=""))
        res = await qa_bee.execute_browser_verification(
            target_url="http://localhost:8000/preview/",
            goal="Submit form and verify toast",
            run_id=qa_run_id,
        )

        assert res["status"] == "pass"
        assert res["verdict"] == "PASS"
    finally:
        if old_perm is None:
            os.environ.pop("SWARM_PERMISSION_MODE", None)
        else:
            os.environ["SWARM_PERMISSION_MODE"] = old_perm


@pytest.mark.asyncio
async def test_qa_fail_fix_pass_loop(qa_run_id):
    """
    Verify complete fail -> fix -> pass loop with seeded bug:
    1. Page written with disabled button.
    2. QA Bee evaluates and returns FAIL.
    3. Queen analyzes failure, routes to fe_worker in channel qa.
    4. fe_worker applies fix.
    5. QA Bee re-tests and returns PASS.
    """
    old_perm = os.environ.get("SWARM_PERMISSION_MODE")
    old_demo = os.environ.get("SWARM_DEMO_MODE")
    os.environ["SWARM_PERMISSION_MODE"] = "demo"
    os.environ["SWARM_DEMO_MODE"] = "seeded_bug"

    try:
        bus = MessageBus(run_id=qa_run_id)
        queen = QueenAgent(bus)
        fe_worker = WorkerAgent("fe_worker", Lane.FE, bus)
        qa_bee = QABee(bus, client=TinyFishClient(api_key=""))

        # 1. FE Worker writes initial page WITH seeded bug
        await fe_worker._write_frontend_project(run_id=qa_run_id, with_bug=True)

        # 2. QA Bee evaluates -> FAIL
        qa_res_1 = await qa_bee.execute_browser_verification(
            target_url="http://localhost:8000/preview/",
            goal="Submit form",
            run_id=qa_run_id,
        )
        assert qa_res_1["verdict"] == "FAIL"

        # 3. Queen analyzes failure and routes to fe_worker
        routed_agent = await queen.route_qa_failure(qa_res_1, retry_count=1, max_retries=2)
        assert routed_agent == "fe_worker"

        # 4. FE Worker applies fix
        await fe_worker.apply_fix(run_id=qa_run_id)

        # 5. QA Bee re-tests -> PASS!
        qa_res_2 = await qa_bee.execute_browser_verification(
            target_url="http://localhost:8000/preview/",
            goal="Submit form",
            run_id=qa_run_id,
        )
        assert qa_res_2["verdict"] == "PASS"

    finally:
        if old_perm is None:
            os.environ.pop("SWARM_PERMISSION_MODE", None)
        else:
            os.environ["SWARM_PERMISSION_MODE"] = old_perm
        if old_demo is None:
            os.environ.pop("SWARM_DEMO_MODE", None)
        else:
            os.environ["SWARM_DEMO_MODE"] = old_demo


@pytest.mark.asyncio
async def test_qa_retry_limit_triggers_emergency_gate(qa_run_id):
    """Verify exceeding retry limit (retry > 2) causes Queen to emit emergency approval card."""
    bus = MessageBus(run_id=qa_run_id)
    cards = []
    approvals = []

    async def mock_card(c):
        cards.append(c)

    async def mock_appr(a):
        approvals.append(a)

    bus.publish_card_upsert = mock_card  # type: ignore
    bus.publish_approval_request = mock_appr  # type: ignore

    queen = QueenAgent(bus)

    failed_result = {
        "status": "fail",
        "verdict": "FAIL",
        "details": "Persistent timeout on submit action.",
    }

    # First attempt: routes to worker
    routed_1 = await queen.route_qa_failure(failed_result, retry_count=1, max_retries=2)
    assert routed_1 == "fe_worker"

    # Second attempt: routes to worker
    routed_2 = await queen.route_qa_failure(failed_result, retry_count=2, max_retries=2)
    assert routed_2 == "fe_worker"

    # Third attempt (exceeds max_retries=2): triggers emergency gate
    routed_3 = await queen.route_qa_failure(failed_result, retry_count=3, max_retries=2)
    assert routed_3 == "emergency_gate"

    # Verify emergency card and approval request were emitted
    assert any(c.id == "card-qa-emergency" and c.status == CardStatus.NEEDS_APPROVAL for c in cards)
    assert any(a.card_id == "card-qa-emergency" for a in approvals)
