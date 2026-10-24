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
}

export type WebSocketEventType =
  | 'feed_message'
  | 'card_upsert'
  | 'approval_request'
  | 'user_message'
  | 'approval_response';

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
    };
