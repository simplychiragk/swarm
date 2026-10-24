"""
FastAPI Sidecar for Swarm.
Provides:
- /health for heartbeat checks
- /ws for real-time WebSocket event streaming to Tauri/React desktop app
- Mock event streamer for the waitlist landing page scenario
- Decision layer stub endpoints for testing routing, approvals, and whiteboard filtering
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sidecar.broadcaster import broadcaster
from sidecar.mock_runner import mock_runner
from sidecar.decision import RuleBasedDecisionLayer
from sidecar.models.contracts import FeedMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("swarm.sidecar")

decision_engine = RuleBasedDecisionLayer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Swarm FastAPI sidecar starting up...")
    yield
    logger.info("Swarm FastAPI sidecar shutting down...")
    mock_runner.stop()


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
        "connections": len(broadcaster.active_connections),
        "mock_running": mock_runner.is_running,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for connected frontend clients.
    Broadcasts incoming agent feed messages, whiteboard card updates, and approval gates.
    """
    await broadcaster.connect(websocket)

    # When a client connects, auto-trigger the mock scenario if not already running
    # so the user sees the live stream immediately!
    if not mock_runner.is_running:
        logger.info("New client connected; initiating mock scenario stream.")
        mock_runner.start(delay_seconds=1.2)

    try:
        while True:
            # Keep connection alive and accept incoming messages from UI (e.g. approval decisions)
            data = await websocket.receive_text()
            logger.info(f"Received message from client: {data}")
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


@app.post("/decision/whiteboard-filter")
async def whiteboard_filter_endpoint(message: FeedMessage):
    """Check if a message warrants a honeycomb whiteboard summary card."""
    show = decision_engine.should_show_on_whiteboard(message)
    return {"message_id": message.id, "show_on_whiteboard": show}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SWARM_SIDECAR_PORT", 8000))
    uvicorn.run("sidecar.main:app", host="127.0.0.1", port=port, reload=True)
