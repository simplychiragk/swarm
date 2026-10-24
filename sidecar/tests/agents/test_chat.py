"""
Unit tests for Stage 4: Real-time agent chat, channel routing, threading,
auto-summarization, decision board, and live agent status events.
"""

import pytest
import asyncio
from sidecar.agents.bus import MessageBus
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    FeedMessage,
    CardStatus,
)
from sidecar.storage import get_storage


@pytest.mark.asyncio
async def test_channel_routing_and_isolation():
    """Verify that messages in 'build' channel only reach build channel members."""
    bus = MessageBus(run_id="run-chat-test")

    # Register agents
    fe_inbox = bus.register_agent("fe_worker", channels=["hive", "build"])
    be_inbox = bus.register_agent("be_worker", channels=["hive", "build"])
    qa_inbox = bus.register_agent("qa_bee", channels=["hive", "qa"])

    msg = FeedMessage(
        id="msg-build-1",
        timestamp="2026-10-24T22:50:00Z",
        sender=AgentSender.WORKER,
        lane=Lane.FE,
        type=MessageType.CHAT,
        content="Connecting to backend endpoint",
        channel="build",
    )
    # fe_worker emits message
    await bus.publish_feed_message(msg)

    # be_worker should have received it
    assert not be_inbox.empty()
    received = await be_inbox.get()
    assert received.id == "msg-build-1"

    # qa_bee should NOT have received it (not in 'build' channel)
    assert qa_inbox.empty()


@pytest.mark.asyncio
async def test_direct_messaging_to_and_mentions():
    """Verify direct messaging via 'to' and explicit 'mentions'."""
    bus = MessageBus(run_id="run-chat-direct")

    queen_inbox = bus.register_agent("queen", channels=["hive", "plan"])
    be_inbox = bus.register_agent("be_worker", channels=["hive", "build"])
    fe_inbox = bus.register_agent("fe_worker", channels=["hive", "build"])

    # Direct message to be_worker
    dm = FeedMessage(
        id="msg-dm-1",
        timestamp="2026-10-24T22:50:00Z",
        sender=AgentSender.QUEEN,
        lane=Lane.NONE,
        type=MessageType.CHAT,
        content="Please verify the schema",
        to="be_worker",
    )
    await bus.publish_feed_message(dm)

    assert not be_inbox.empty()
    assert fe_inbox.empty()
    assert (await be_inbox.get()).content == "Please verify the schema"

    # Mention fe_worker
    mention_msg = FeedMessage(
        id="msg-mention-1",
        timestamp="2026-10-24T22:50:00Z",
        sender=AgentSender.WORKER,
        lane=Lane.BE,
        type=MessageType.CHAT,
        content="@fe_worker waitlist POST schema is ready",
        mentions=["fe_worker"],
    )
    await bus.publish_feed_message(mention_msg)

    assert not fe_inbox.empty()
    assert (await fe_inbox.get()).id == "msg-mention-1"


@pytest.mark.asyncio
async def test_threading_and_turn_tracking():
    """Verify thread_id tracking increments turns correctly."""
    bus = MessageBus(run_id="run-chat-thread")
    bus.register_agent("fe_worker", channels=["hive", "build"])

    thread_id = "thread-form-design"

    for i in range(1, 6):
        msg = FeedMessage(
            id=f"msg-turn-{i}",
            timestamp="2026-10-24T22:50:00Z",
            sender=AgentSender.WORKER,
            lane=Lane.FE,
            type=MessageType.CHAT,
            content=f"Turn message {i}",
            channel="build",
            thread_id=thread_id,
        )
        await bus.publish_feed_message(msg)

    assert bus.get_thread_turns(thread_id) == 5


@pytest.mark.asyncio
async def test_thread_auto_summarization():
    """Verify thread auto-summarizes and records to DB when threshold turns are reached."""
    # Threshold = 4 for testing
    bus = MessageBus(run_id="run-chat-auto-sum", auto_summary_threshold=4)
    bus.register_agent("fe_worker", channels=["hive", "build"])

    thread_id = "thread-high-turn"

    for i in range(1, 5):
        msg = FeedMessage(
            id=f"msg-sum-{i}",
            timestamp="2026-10-24T22:50:00Z",
            sender=AgentSender.WORKER,
            lane=Lane.FE,
            type=MessageType.CHAT,
            content=f"Discussion turn {i}",
            channel="build",
            thread_id=thread_id,
        )
        await bus.publish_feed_message(msg)

    # Check DB for thread record
    storage = get_storage()
    cur = storage.db.execute_read(
        "SELECT * FROM threads WHERE run_id = ? AND id = ?;",
        ("run-chat-auto-sum", thread_id),
    )
    row = cur.fetchone()
    assert row is not None
    assert row["status"] == "summarized"
    assert row["turn_count"] >= 4


@pytest.mark.asyncio
async def test_decision_board_recording():
    """Verify intent='decision' automatically stores in decisions table and posts whiteboard card."""
    bus = MessageBus(run_id="run-chat-decisions")
    cards_upserted = []

    async def mock_upsert(card, provenance="real"):
        cards_upserted.append(card)

    bus.publish_card_upsert = mock_upsert  # type: ignore

    decision_msg = FeedMessage(
        id="msg-dec-1",
        timestamp="2026-10-24T22:50:00Z",
        sender=AgentSender.WORKER,
        lane=Lane.BE,
        type=MessageType.CHAT,
        content="Agreed on POST /api/waitlist accepting {name, email, role} and returning 201.",
        channel="build",
        thread_id="thread-api-contract",
        intent="decision",
        metadata={
            "topic": "Waitlist API Request Contract",
            "agreed_by": ["be_worker", "fe_worker"],
        },
    )

    await bus.publish_feed_message(decision_msg)

    # 1. Whiteboard card should have been posted
    assert len(cards_upserted) == 1
    card = cards_upserted[0]
    assert card.status == CardStatus.DONE
    assert "Waitlist API Request Contract" in card.title
    assert len(card.evidence) >= 1
    assert "be_worker" in card.evidence[0].url_or_text

    # 2. Database decisions table should have recorded it
    storage = get_storage()
    decisions = storage.get_run_decisions("run-chat-decisions")
    assert len(decisions) >= 1
    assert decisions[0]["topic"] == "Waitlist API Request Contract"
    assert "fe_worker" in decisions[0]["agreed_by"]


@pytest.mark.asyncio
async def test_agent_status_and_feed_chunk_broadcast():
    """Verify live agent status and feed chunk helper broadcasting."""
    bus = MessageBus(run_id="run-chat-status")
    broadcasted = []

    from sidecar.broadcaster import broadcaster

    orig_broadcast = broadcaster.broadcast

    async def mock_bc(evt, run_id="run-default", provenance="real"):
        broadcasted.append((evt, run_id, provenance))

    broadcaster.broadcast = mock_bc  # type: ignore

    try:
        # Publish agent status
        await bus.publish_agent_status(
            agent="fe_worker",
            status="working",
            current_task="Rendering form validation error state",
            lane=Lane.FE,
        )

        assert len(broadcasted) == 1
        status_env = broadcasted[0][0]
        assert status_env["event"] == "agent_status"
        assert status_env["payload"]["agent"] == "fe_worker"
        assert status_env["payload"]["status"] == "working"

        # Publish feed chunk
        await bus.publish_feed_chunk(
            message_id="msg-stream-1",
            delta="export default function App() {",
            turn=1,
            is_final=False,
        )

        assert len(broadcasted) == 2
        chunk_env = broadcasted[1][0]
        assert chunk_env["event"] == "feed_chunk"
        assert chunk_env["payload"]["message_id"] == "msg-stream-1"
        assert chunk_env["payload"]["delta"] == "export default function App() {"

    finally:
        broadcaster.broadcast = orig_broadcast
