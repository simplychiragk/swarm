"""
Tests for Swarm Agent Engine:
- Interview ends after 3 questions
- Structured plan parsing and lane delegation
- Worker peer message exchange
- Scribe message batching and card emission
- Run limits and safety triggers
- End-to-end run from user prompt to approval resolution
"""

import asyncio
import pytest
from unittest.mock import patch

from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
    UserMessage,
    ApprovalResponse,
)
from sidecar.agents.bus import MessageBus
from sidecar.agents.queen import QueenAgent
from sidecar.agents.worker import WorkerAgent
from sidecar.agents.scribe import ScribeAgent
from sidecar.agents.run_manager import SwarmRunManager
from sidecar.agents.base import AgentMessageLimitError


@pytest.mark.asyncio
async def test_interview_stops_after_max_questions():
    """Verify that the Queen asks at most 3 questions and concludes discovery."""
    bus = MessageBus()
    queen = QueenAgent(bus)

    # Message 1
    await queen.handle_user_input("I want an app.")
    assert queen.question_count == 1
    assert not queen.interview_done

    # Message 2
    await queen.handle_user_input("A web application.")
    assert queen.question_count == 2
    assert not queen.interview_done

    # Message 3 - must end discovery
    await queen.handle_user_input("For indie developers with dark theme.")
    assert queen.question_count == 3
    assert queen.interview_done
    assert queen.plan_done


@pytest.mark.asyncio
async def test_plan_parses_and_routes_tasks():
    """Verify that Queen generates a valid plan and delegates to lanes."""
    bus = MessageBus()
    queen = QueenAgent(bus)

    # Provide full initial requirements so plan generates immediately
    await queen.handle_user_input("Build dark honeycomb landing page with waitlist form capturing name and email.")
    assert queen.interview_done
    assert queen.plan_done
    assert len(queen.tasks_created) >= 2

    # Verify task messages were published to the bus
    task_messages = [m for m in bus.get_history() if m.type == MessageType.TASK]
    assert len(task_messages) >= 2


@pytest.mark.asyncio
async def test_workers_peer_exchange():
    """Verify BE Worker broadcasts API contract and FE Worker acknowledges it."""
    bus = MessageBus()
    be_worker = WorkerAgent("be_worker", Lane.BE, bus)
    fe_worker = WorkerAgent("fe_worker", Lane.FE, bus)

    # Route bus to FE worker
    bus.subscribe(fe_worker.receive)

    # BE worker executes task
    await be_worker.execute_task(
        task_id="task-be-1",
        title="FastAPI Route",
        description="Build waitlist endpoint",
    )

    # Process pending messages in FE worker inbox
    while not fe_worker.inbox.empty():
        msg = await fe_worker.inbox.get()
        await fe_worker.process_message(msg)

    assert fe_worker.received_peer_contract is not None
    assert "/api/waitlist" in fe_worker.received_peer_contract


@pytest.mark.asyncio
async def test_scribe_batches_and_emits_cards():
    """Verify that Scribe summarizes recent feed messages into a whiteboard card."""
    bus = MessageBus()
    cards_published = []
    bus.publish_card_upsert = AsyncMock = lambda c: cards_published.append(c)  # type: ignore

    scribe = ScribeAgent(bus, batch_interval=0.1)

    # Publish milestone messages
    await scribe.process_message(
        FeedMessage(
            id="m1",
            timestamp="2026-10-24T12:00:00Z",
            sender=AgentSender.WORKER,
            lane=Lane.BE,
            type=MessageType.STATUS,
            content="BE Worker: /api/waitlist passes all checks.",
        )
    )

    scribe.start()
    await asyncio.sleep(0.3)
    await scribe.stop()

    assert len(cards_published) >= 1
    assert cards_published[0].title


@pytest.mark.asyncio
async def test_message_limit_guard():
    """Verify that exceeding max_messages raises AgentMessageLimitError."""
    bus = MessageBus()
    worker = WorkerAgent("worker_strict", Lane.FE, bus)
    worker.max_messages = 2

    await worker.emit_feed_message(MessageType.CHAT, "Msg 1")
    await worker.emit_feed_message(MessageType.CHAT, "Msg 2")

    with pytest.raises(AgentMessageLimitError):
        await worker.emit_feed_message(MessageType.CHAT, "Msg 3")


@pytest.mark.asyncio
async def test_end_to_end_run_to_approval():
    """
    Test full live-mode pipeline:
    user_message -> interview -> plan -> BE/FE execution -> approval_request -> approval_response
    """
    manager = SwarmRunManager(global_timeout_seconds=30.0)

    # Track broadcast envelopes
    published_cards = []
    published_approvals = []

    async def mock_card(card):
        published_cards.append(card)

    async def mock_appr(req):
        published_approvals.append(req)

    manager.bus.publish_card_upsert = mock_card  # type: ignore
    manager.bus.publish_approval_request = mock_appr  # type: ignore

    user_msg = UserMessage(
        id="user-1",
        text="Build dark modern waitlist landing page for developers.",
        timestamp="2026-10-24T12:00:00Z",
    )

    # Start run with user message
    await manager.handle_user_message(user_msg)

    # Await pipeline completion
    if manager._orchestrator_task:
        await manager._orchestrator_task

    # Verify approval request was triggered
    assert manager.approval_pending is True
    assert len(published_approvals) >= 1
    assert published_approvals[0].card_id == "card-release-gate"

    # User approves
    approval = ApprovalResponse(
        approval_id=published_approvals[0].id,
        card_id=published_approvals[0].card_id,
        decision="approve",
    )
    await manager.handle_approval(approval)

    # Card must now be DONE
    final_card = published_cards[-1]
    assert final_card.status == CardStatus.DONE
    assert final_card.id == "card-release-gate"

    await manager.stop()
