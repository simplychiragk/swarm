"""
FastAPI Sidecar for Swarm.
Provides:
- /health for heartbeat checks
- /ws for real-time bidirectional WebSocket event streaming with Tauri/React app
- Mock event streamer for the waitlist landing page scenario
- Decision layer stub endpoints for testing routing, approvals, and whiteboard filtering
- RunManager integration for live agent orchestration
"""

import os
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from sidecar.broadcaster import broadcaster
from sidecar.mock_runner import mock_runner
from sidecar.decision import RuleBasedDecisionLayer
from sidecar.models.contracts import (
    AgentSender,
    Lane,
    MessageType,
    CardStatus,
    FeedMessage,
    WhiteboardCard,
    FeedMessageEnvelope,
    CardUpsertEnvelope,
    UserMessage,
    ApprovalResponse,
    InboundEnvelope,
    parse_inbound_envelope,
)
from sidecar.runtime.run_manager import RunManager, NoOpRunManager
from sidecar.agents.run_manager import SwarmRunManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("swarm.sidecar")

decision_engine = RuleBasedDecisionLayer()
active_run_manager: RunManager = SwarmRunManager()


def get_swarm_mode() -> str:
    return os.environ.get("SWARM_MODE", "mock").strip().lower()


def set_run_manager(manager: RunManager) -> None:
    """Configures the active run manager for live mode."""
    global active_run_manager
    active_run_manager = manager


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = get_swarm_mode()
    logger.info(f"Swarm FastAPI sidecar starting up in SWARM_MODE={mode}...")
    yield
    logger.info("Swarm FastAPI sidecar shutting down...")
    mock_runner.stop()
    if hasattr(active_run_manager, "stop"):
        await active_run_manager.stop()


app = FastAPI(
    title="Swarm Sidecar",
    description="Agent orchestration, decision layer stub, and WebSocket broadcaster for Swarm",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS enabled for local development and Tauri shell
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Heartbeat endpoint for Tauri and health checkers."""
    return {
        "status": "ok",
        "app": "swarm-sidecar",
        "version": "0.1.0",
        "mode": get_swarm_mode(),
        "connections": len(broadcaster.active_connections),
        "mock_running": mock_runner.is_running,
    }


async def handle_inbound_envelope(envelope: InboundEnvelope) -> None:
    """Route inbound client envelope based on SWARM_MODE."""
    mode = get_swarm_mode()
    logger.info(f"Handling client event '{envelope.event}' in mode '{mode}'")

    if mode == "mock":
        if envelope.event == "user_message":
            user_msg: UserMessage = envelope.payload
            reply_id = f"msg-queen-reply-{uuid.uuid4().hex[:6]}"
            queen_reply = FeedMessageEnvelope(
                payload=FeedMessage(
                    id=reply_id,
                    timestamp=now_iso(),
                    sender=AgentSender.QUEEN,
                    lane=Lane.NONE,
                    type=MessageType.CHAT,
                    content=f"Queen: Acknowledged '{user_msg.text}'. Factoring your instructions into worker tasks.",
                    metadata={"in_reply_to": user_msg.id},
                )
            ).model_dump()
            await broadcaster.broadcast(queen_reply)

        elif envelope.event == "approval_response":
            approval_resp: ApprovalResponse = envelope.payload
            new_status = CardStatus.DONE if approval_resp.decision == "approve" else CardStatus.FAILED
            card_title = "Production Release Gate"
            card_summary = (
                "Release approved by user. Proceeding to deployment."
                if approval_resp.decision == "approve"
                else f"Release redirected by user: {approval_resp.note or 'Revising components.'}"
            )

            # Broadcast updated card
            card_update = CardUpsertEnvelope(
                payload=WhiteboardCard(
                    id=approval_resp.card_id,
                    title=card_title,
                    summary=card_summary,
                    status=new_status,
                    lane=Lane.OPS,
                    updated_at=now_iso(),
                )
            ).model_dump()
            await broadcaster.broadcast(card_update)

            # Broadcast Queen status
            status_update = FeedMessageEnvelope(
                payload=FeedMessage(
                    id=f"msg-approval-{uuid.uuid4().hex[:6]}",
                    timestamp=now_iso(),
                    sender=AgentSender.QUEEN,
                    lane=Lane.OPS,
                    type=MessageType.STATUS,
                    content=f"Queen: User selected '{approval_resp.decision}' for card {approval_resp.card_id}. Whiteboard updated.",
                    metadata={"approval_id": approval_resp.approval_id, "decision": approval_resp.decision},
                )
            ).model_dump()
            await broadcaster.broadcast(status_update)

    else:
        # Live mode delegates to RunManager
        if envelope.event == "user_message":
            await active_run_manager.handle_user_message(envelope.payload)
        elif envelope.event == "approval_response":
            await active_run_manager.handle_approval(envelope.payload)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Bidirectional WebSocket endpoint for connected frontend clients.
    Broadcasts agent feed messages, whiteboard card updates, and approval gates.
    Accepts, validates, and routes client user_message and approval_response events.
    """
    await broadcaster.connect(websocket)

    # In mock mode, auto-trigger the mock scenario on client connection if not already running
    # In live mode, mock runner must NOT auto-start!
    if get_swarm_mode() == "mock" and not mock_runner.is_running:
        logger.info("New client connected in mock mode; initiating mock scenario stream.")
        mock_runner.start(delay_seconds=1.2)

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                envelope = parse_inbound_envelope(raw_text)
                await handle_inbound_envelope(envelope)
            except ValidationError as ve:
                logger.warning(f"Invalid inbound event envelope rejected: {ve}")
                err_msg = FeedMessageEnvelope(
                    payload=FeedMessage(
                        id=f"msg-err-{uuid.uuid4().hex[:6]}",
                        timestamp=now_iso(),
                        sender=AgentSender.SYSTEM,
                        lane=Lane.NONE,
                        type=MessageType.ERROR,
                        content=f"Validation error for client event: {ve.errors()[0]['msg']}",
                    )
                ).model_dump()
                await websocket.send_text(str(err_msg))
            except Exception as e:
                logger.error(f"Error processing client message: {e}", exc_info=True)
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        broadcaster.disconnect(websocket)


class MockControlRequest(BaseModel):
    delay_seconds: float = 1.0


@app.post("/mock/start")
async def start_mock_scenario(req: Optional[MockControlRequest] = None):
    """Trigger the Section 9 waitlist scenario fake run."""
    delay = req.delay_seconds if req else 1.0
    started = mock_runner.start(delay_seconds=delay)
    return {"started": started, "is_running": mock_runner.is_running}


@app.post("/mock/reset")
async def reset_mock_scenario():
    """Reset history and stop any active mock stream."""
    mock_runner.stop()
    broadcaster.clear_history()
    return {"status": "reset", "history_len": 0}


class RouteTaskRequest(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = None


@app.post("/decision/route")
async def route_task_endpoint(req: RouteTaskRequest):
    """Route a task description to a lane via decision layer."""
    lane = decision_engine.route_task(req.task, req.context)
    return {"task": req.task, "lane": lane.value}


class NeedsApprovalRequest(BaseModel):
    action: str
    context: Optional[Dict[str, Any]] = None


@app.post("/decision/needs-approval")
async def needs_approval_endpoint(req: NeedsApprovalRequest):
    """Check if an action requires approval."""
    needs_app = decision_engine.needs_approval(req.action, req.context)
    return {"action": req.action, "needs_approval": needs_app}


class WhiteboardFilterRequest(BaseModel):
    message: FeedMessage


@app.post("/decision/whiteboard-filter")
async def whiteboard_filter_endpoint(req: WhiteboardFilterRequest):
    """Check if a message warrants a honeycomb whiteboard summary card."""
    show = decision_engine.should_show_on_whiteboard(req.message)
    return {"message_id": req.message.id, "show_on_whiteboard": show}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SWARM_SIDECAR_PORT", 8000))
    uvicorn.run("sidecar.main:app", host="127.0.0.1", port=port, reload=True)
