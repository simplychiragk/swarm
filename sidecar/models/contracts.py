"""
Swarm Shared Contracts - Pydantic Models
Directly aligned with shared/schemas/ and shared/types/contracts.ts
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union, Literal, Annotated
from pydantic import BaseModel, Field, TypeAdapter


class AgentSender(str, Enum):
    QUEEN = "queen"
    WORKER = "worker"
    SCRIBE = "scribe"
    QA = "qa"
    RESEARCH = "research"
    SYSTEM = "system"


class Lane(str, Enum):
    FE = "FE"
    BE = "BE"
    DB = "DB"
    DESIGN = "Design"
    TEST = "Test"
    DOCS = "Docs"
    OPS = "Ops"
    NONE = "none"


class MessageType(str, Enum):
    CHAT = "chat"
    TASK = "task"
    STATUS = "status"
    EVIDENCE = "evidence"
    ERROR = "error"


class CardStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    NEEDS_APPROVAL = "needs_approval"
    FAILED = "failed"


class EvidenceItem(BaseModel):
    kind: str = Field(..., description="Type of evidence, e.g. screenshot, log, diff")
    url_or_text: str = Field(..., description="URL or textual snippet")


class FeedMessage(BaseModel):
    id: str
    timestamp: str = Field(..., description="ISO 8601 string")
    sender: AgentSender
    lane: Lane = Lane.NONE
    type: MessageType = MessageType.CHAT
    content: str
    metadata: Optional[Dict[str, Any]] = None
    channel: Optional[str] = "hive"
    to: Optional[str] = None
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None
    mentions: Optional[List[str]] = None
    intent: Optional[Literal["chat", "proposal", "critique", "decision", "handoff", "blocked"]] = "chat"
    requires_response: Optional[bool] = False


class AgentStatus(BaseModel):
    agent: str
    status: Literal["idle", "thinking", "working", "blocked"]
    current_task: Optional[str] = None
    lane: Optional[Lane] = Lane.NONE
    timestamp: str = Field(..., description="ISO 8601 string")


class FeedChunk(BaseModel):
    message_id: str
    delta: str
    turn: Optional[int] = 0
    is_final: Optional[bool] = False
    timestamp: str = Field(..., description="ISO 8601 string")


class WhiteboardCard(BaseModel):
    id: str
    title: str
    summary: str
    status: CardStatus
    lane: Lane = Lane.NONE
    evidence: Optional[List[EvidenceItem]] = None
    updated_at: str = Field(..., description="ISO 8601 string")


class ApprovalRequest(BaseModel):
    id: str
    card_id: str
    prompt: str
    options: List[str]
    lane: Lane = Lane.NONE
    card: Optional[WhiteboardCard] = None
    created_at: str = Field(..., description="ISO 8601 string")
    tool: Optional[str] = None
    args_preview: Optional[str] = None
    risk: Optional[Literal["low", "medium", "high"]] = None
    reason: Optional[str] = None
    agent: Optional[str] = None
    scope_options: Optional[List[str]] = None
    expires_in_s: Optional[Union[int, float]] = None


class UserMessage(BaseModel):
    id: str
    text: str
    timestamp: str = Field(..., description="ISO 8601 string")
    mode: Optional[Literal["steer", "queue", "interrupt"]] = "steer"


class TaskDiffItem(BaseModel):
    task_id: str
    title: str
    action: Literal["added", "modified", "removed"]
    lane: Lane
    reason: str


class PlanDiff(BaseModel):
    run_id: str
    reason: str
    changes: List[TaskDiffItem]
    timestamp: str


class PlanDiffEnvelope(BaseModel):
    event: Literal["plan_diff"] = "plan_diff"
    payload: PlanDiff


class ApprovalResponse(BaseModel):
    approval_id: str
    card_id: str
    decision: Literal["approve", "redirect"]
    note: Optional[str] = None
    scope: Optional[Literal["once", "run", "deny"]] = None


class FeedMessageEnvelope(BaseModel):
    event: Literal["feed_message"] = "feed_message"
    payload: FeedMessage


class CardUpsertEnvelope(BaseModel):
    event: Literal["card_upsert"] = "card_upsert"
    payload: WhiteboardCard


class ApprovalRequestEnvelope(BaseModel):
    event: Literal["approval_request"] = "approval_request"
    payload: ApprovalRequest


class UserMessageEnvelope(BaseModel):
    event: Literal["user_message"] = "user_message"
    payload: UserMessage


class ApprovalResponseEnvelope(BaseModel):
    event: Literal["approval_response"] = "approval_response"
    payload: ApprovalResponse


class AgentStatusEnvelope(BaseModel):
    event: Literal["agent_status"] = "agent_status"
    payload: AgentStatus


class FeedChunkEnvelope(BaseModel):
    event: Literal["feed_chunk"] = "feed_chunk"
    payload: FeedChunk


EventEnvelope = Annotated[
    Union[
        FeedMessageEnvelope,
        CardUpsertEnvelope,
        ApprovalRequestEnvelope,
        UserMessageEnvelope,
        ApprovalResponseEnvelope,
        AgentStatusEnvelope,
        FeedChunkEnvelope,
        PlanDiffEnvelope,
    ],
    Field(discriminator="event"),
]

InboundEnvelope = Annotated[
    Union[
        UserMessageEnvelope,
        ApprovalResponseEnvelope,
    ],
    Field(discriminator="event"),
]

_event_adapter = TypeAdapter(EventEnvelope)
_inbound_adapter = TypeAdapter(InboundEnvelope)


def parse_event_envelope(raw_json: Union[str, bytes]) -> EventEnvelope:
    """Parse and validate any EventEnvelope string."""
    return _event_adapter.validate_json(raw_json)


def parse_inbound_envelope(raw_json: Union[str, bytes]) -> InboundEnvelope:
    """Parse and validate a client-to-server EventEnvelope."""
    return _inbound_adapter.validate_json(raw_json)
