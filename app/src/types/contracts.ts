/**
 * Swarm Shared Contracts (Frontend Mirror)
 * Kept aligned with shared/types/contracts.ts
 */

export type AgentSender = 'queen' | 'worker' | 'scribe' | 'qa' | 'research' | 'system';

export type Lane = 'FE' | 'BE' | 'DB' | 'Design' | 'Test' | 'Docs' | 'Ops' | 'none';

export type MessageType = 'chat' | 'task' | 'status' | 'evidence' | 'error';

export type CardStatus = 'planned' | 'in_progress' | 'done' | 'needs_approval' | 'failed';

export interface EvidenceItem {
  kind: string;
  url_or_text: string;
}

export interface FeedMessage {
  id: string;
  timestamp: string; // ISO 8601
  sender: AgentSender;
  lane: Lane;
  type: MessageType;
  content: string;
  metadata?: Record<string, unknown>;
  channel?: string;
  to?: string;
  thread_id?: string;
  reply_to?: string;
  mentions?: string[];
  intent?: 'chat' | 'proposal' | 'critique' | 'decision' | 'handoff' | 'blocked';
  requires_response?: boolean;
}

export interface AgentStatus {
  agent: string;
  status: 'idle' | 'thinking' | 'working' | 'blocked';
  current_task?: string;
  lane?: Lane;
  timestamp: string; // ISO 8601
}

export interface FeedChunk {
  message_id: string;
  delta: string;
  turn?: number;
  is_final?: boolean;
  timestamp: string; // ISO 8601
}

export interface WhiteboardCard {
  id: string;
  title: string;
  summary: string;
  status: CardStatus;
  lane: Lane;
  evidence?: EvidenceItem[];
  updated_at: string; // ISO 8601
}

export interface ApprovalRequest {
  id: string;
  card_id: string;
  prompt: string;
  options: string[];
  lane: Lane;
  card?: WhiteboardCard;
  created_at: string; // ISO 8601
  tool?: string;
  args_preview?: string;
  risk?: 'low' | 'medium' | 'high';
  reason?: string;
  agent?: string;
  scope_options?: string[];
  expires_in_s?: number;
}

export interface UserMessage {
  id: string;
  text: string;
  timestamp: string; // ISO 8601
}

export interface ApprovalResponse {
  approval_id: string;
  card_id: string;
  decision: 'approve' | 'redirect';
  note?: string;
  scope?: 'once' | 'run' | 'deny';
}

export type WebSocketEventType =
  | 'feed_message'
  | 'card_upsert'
  | 'approval_request'
  | 'user_message'
  | 'approval_response'
  | 'agent_status'
  | 'feed_chunk';

export type EventEnvelope =
  | {
      event: 'feed_message';
      payload: FeedMessage;
    }
  | {
      event: 'card_upsert';
      payload: WhiteboardCard;
    }
  | {
      event: 'approval_request';
      payload: ApprovalRequest;
    }
  | {
      event: 'user_message';
      payload: UserMessage;
    }
  | {
      event: 'approval_response';
      payload: ApprovalResponse;
    }
  | {
      event: 'agent_status';
      payload: AgentStatus;
    }
  | {
      event: 'feed_chunk';
      payload: FeedChunk;
    };
