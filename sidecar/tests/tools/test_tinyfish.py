"""
Tests for TinyFish tools integration:
- TinyFishClient in mock mode (search, fetch, run_browser_task)
- Fallback to mock when key is not set or in mock mode
- ResearchBee evidence generation
- QABee browser verification with evidence
"""

import os
import pytest
from sidecar.models.contracts import CardStatus, MessageType
from sidecar.tools.client import TinyFishClient
from sidecar.tools.agents import ResearchBee, QABee
from sidecar.agents.bus import MessageBus


@pytest.fixture(autouse=True)
def force_mock_tinyfish():
    old = os.environ.get("SWARM_TINYFISH_MODE")
    old_perm = os.environ.get("SWARM_PERMISSION_MODE")
    os.environ["SWARM_TINYFISH_MODE"] = "mock"
    os.environ["SWARM_PERMISSION_MODE"] = "demo"
    yield
    if old is None:
        os.environ.pop("SWARM_TINYFISH_MODE", None)
    else:
        os.environ["SWARM_TINYFISH_MODE"] = old
    if old_perm is None:
        os.environ.pop("SWARM_PERMISSION_MODE", None)
    else:
        os.environ["SWARM_PERMISSION_MODE"] = old_perm


@pytest.mark.asyncio
async def test_tinyfish_client_mock_search():
    """Verify search returns realistic documentation snippets in mock mode."""
    client = TinyFishClient(api_key="")
    res = await client.search("react form validation patterns")
    assert "results" in res
    assert len(res["results"]) >= 1
    assert "Zod" in res["results"][0]["snippet"] or "React" in res["results"][0]["title"]


@pytest.mark.asyncio
async def test_tinyfish_client_mock_fetch():
    """Verify fetch extracts page text in mock mode."""
    client = TinyFishClient(api_key="")
    res = await client.fetch("https://react.dev")
    assert res["status"] == "COMPLETED"
    assert "React" in res["content"]


@pytest.mark.asyncio
async def test_tinyfish_client_mock_browser_task():
    """Verify run_browser_task returns screenshot and pass status."""
    client = TinyFishClient(api_key="")
    res = await client.run_browser_task("http://localhost:5173", "Submit form")
    assert res["status"] == "COMPLETED"
    assert res["result"]["verdict"] == "PASS"
    assert "screenshot" in res["evidence"]["kind"]
    assert res["evidence"]["url_or_text"].endswith(".png")


@pytest.mark.asyncio
async def test_research_bee_evidence_card():
    """Verify ResearchBee publishes evidence feed messages and cards."""
    bus = MessageBus()
    cards = []

    async def mock_upsert(c):
        cards.append(c)

    bus.publish_card_upsert = mock_upsert  # type: ignore

    bee = ResearchBee(bus, client=TinyFishClient(api_key=""))
    await bee.execute_research("form validation")

    assert len(cards) == 1
    assert cards[0].id == "card-research"
    assert cards[0].status == CardStatus.DONE
    assert len(cards[0].evidence) >= 1


@pytest.mark.asyncio
async def test_qa_bee_browser_verification_card():
    """Verify QABee attaches screenshot and log evidence to whiteboard card."""
    bus = MessageBus()
    cards = []

    async def mock_upsert(c):
        cards.append(c)

    bus.publish_card_upsert = mock_upsert  # type: ignore

    bee = QABee(bus, client=TinyFishClient(api_key=""))
    await bee.execute_browser_verification("http://localhost:5173", "Verify form")

    assert len(cards) == 1
    assert cards[0].id == "card-qa-verify"
    assert cards[0].status == CardStatus.DONE
    assert any(e.kind == "screenshot" for e in cards[0].evidence)


@pytest.mark.asyncio
async def test_research_bee_waitlist_plan_grounding():
    """Verify ResearchBee searches for waitlist form fields, fetches top result, and posts plan grounding proposal."""
    bus = MessageBus()
    feed_messages = []
    cards = []

    async def mock_feed(m):
        feed_messages.append(m)

    async def mock_card(c):
        cards.append(c)

    bus.subscribe(mock_feed)
    bus.publish_card_upsert = mock_card  # type: ignore

    bee = ResearchBee(bus, client=TinyFishClient(api_key=""))
    res = await bee.execute_research("best practice waitlist form fields 2026")

    assert res["status"] == "success"
    assert res["provenance"] == "simulated"

    # Verify plan proposal message was emitted
    proposals = [m for m in feed_messages if m.intent == "proposal" and m.channel == "plan"]
    assert len(proposals) >= 1
    assert "queen" in proposals[0].mentions or "fe_worker" in proposals[0].mentions
