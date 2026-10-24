"""
Swarm Shared Contracts - Pydantic Models
Directly aligned with shared/schemas/ and shared/types/contracts.ts
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field


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


class FeedMessageEnvelope(BaseModel):
    event: Literal["feed_message"] = "feed_message"
    payload: FeedMessage


class CardUpsertEnvelope(BaseModel):
    event: Literal["card_upsert"] = "card_upsert"
    payload: WhiteboardCard


class ApprovalRequestEnvelope(BaseModel):
    event: Literal["approval_request"] = "approval_request"
    payload: ApprovalRequest


EventEnvelope = Union[FeedMessageEnvelope, CardUpsertEnvelope, ApprovalRequestEnvelope]
