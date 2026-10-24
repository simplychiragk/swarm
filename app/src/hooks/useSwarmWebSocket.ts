import { useState, useEffect, useRef, useCallback } from "react";
import type {
  EventEnvelope,
  FeedMessage,
  WhiteboardCard,
  ApprovalRequest,
  CardStatus,
} from "../types/contracts";

const DEFAULT_WS_URL = "ws://127.0.0.1:8000/ws";

export function useSwarmWebSocket(url: string = DEFAULT_WS_URL) {
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const [messages, setMessages] = useState<FeedMessage[]>([]);
  const [cards, setCards] = useState<Record<string, WhiteboardCard>>({});
  const [activeApproval, setActiveApproval] = useState<ApprovalRequest | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isIntentionalCloseRef = useRef<boolean>(false);
  const resolvedApprovalsRef = useRef<Set<string>>(new Set());
  const cardsRef = useRef<Record<string, WhiteboardCard>>({});

  // Keep cardsRef synchronized with cards state for synchronous checks
  useEffect(() => {
    cardsRef.current = cards;
  }, [cards]);

  const connect = useCallback(() => {
    // If socket is already open or currently connecting, do not re-initialize
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    if (socketRef.current) {
      try {
        isIntentionalCloseRef.current = true;
        socketRef.current.close();
      } catch {
        // ignore
      }
    }
    isIntentionalCloseRef.current = false;
    setStatus("connecting");

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data) as EventEnvelope;

          if (envelope.event === "feed_message") {
            setMessages((prev) => [...prev, envelope.payload]);
          } else if (envelope.event === "card_upsert") {
            const card = envelope.payload;
            cardsRef.current = {
              ...cardsRef.current,
              [card.id]: card,
            };
            setCards((prev) => ({
              ...prev,
              [card.id]: card,
            }));

            // If the card is finalized (done or failed), permanently dismiss any active approval for it
            if (card.status === "done" || card.status === "failed") {
              resolvedApprovalsRef.current.add(card.id);
              setActiveApproval((current) => {
                if (current && current.card_id === card.id) {
                  return null;
                }
                return current;
              });
            }
          } else if (envelope.event === "approval_request") {
            const req = envelope.payload;

            // Check if this approval was already decided or its card is already completed
            const isAlreadyResolved =
              resolvedApprovalsRef.current.has(req.id) ||
              resolvedApprovalsRef.current.has(req.card_id);

            const existingCard = cardsRef.current[req.card_id];
            const isCardDone =
              existingCard &&
              (existingCard.status === "done" || existingCard.status === "failed");

            if (isAlreadyResolved || isCardDone) {
              // Discard duplicate or already resolved approval request
              return;
            }

            setActiveApproval(req);
          }
        } catch (err) {
          console.error("Failed to parse WebSocket event:", err);
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        // Only attempt automatic reconnect if this wasn't an intentional cleanup
        if (!isIntentionalCloseRef.current) {
          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, 3000);
        }
      };

      ws.onerror = () => {
        setStatus("disconnected");
      };

      socketRef.current = ws;
    } catch (e) {
      console.error("WebSocket init error:", e);
      setStatus("disconnected");
    }
  }, [url]);

  useEffect(() => {
    isIntentionalCloseRef.current = false;
    connect();
    return () => {
      isIntentionalCloseRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((text: string) => {
    if (!text.trim()) return;

    const payload = {
      id: `user-msg-${Date.now()}`,
      text: text.trim(),
      timestamp: new Date().toISOString(),
    };

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: "user_message",
          payload,
        })
      );
    }

    // Optimistically add to local feed as user message
    setMessages((prev) => [
      ...prev,
      {
        id: payload.id,
        timestamp: payload.timestamp,
        sender: "system",
        lane: "none",
        type: "chat",
        content: `You: ${payload.text}`,
      },
    ]);
  }, []);

  const sendApprovalDecision = useCallback(
    (decision: "approve" | "redirect", note?: string) => {
      if (!activeApproval) return;

      const approvalId = activeApproval.id;
      const cardId = activeApproval.card_id;

      // Lock this approval immediately so it can NEVER re-trigger
      resolvedApprovalsRef.current.add(approvalId);
      resolvedApprovalsRef.current.add(cardId);

      const payload = {
        approval_id: approvalId,
        card_id: cardId,
        decision,
        note: note || (decision === "approve" ? "Approved by user" : "Redirected by user"),
      };

      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({
            event: "approval_response",
            payload,
          })
        );
      }

      const finalStatus: CardStatus = decision === "approve" ? "done" : "failed";

      // Optimistically update card status locally to final state
      setCards((prev) => {
        const target = prev[cardId];
        const updated: Record<string, WhiteboardCard> = {
          ...prev,
          [cardId]: {
            ...(target || {
              id: cardId,
              title: "Production Release Gate",
              lane: "Ops",
              updated_at: new Date().toISOString(),
            }),
            status: finalStatus,
            summary:
              decision === "approve"
                ? "Production release authorized by user. Application deployed live."
                : `Release redirected: ${payload.note}`,
          },
        };
        cardsRef.current = updated;
        return updated;
      });

      // Clear the active approval dialog immediately
      setActiveApproval(null);
    },
    [activeApproval]
  );

  const triggerRun = useCallback(async () => {
    try {
      await fetch("http://127.0.0.1:8000/mock/start", { method: "POST" });
    } catch (e) {
      console.error("Trigger error:", e);
    }
  }, []);

  const resetBoard = useCallback(async () => {
    try {
      await fetch("http://127.0.0.1:8000/mock/reset", { method: "POST" });
    } catch (e) {
      console.error("Reset error:", e);
    }
    resolvedApprovalsRef.current.clear();
    cardsRef.current = {};
    setMessages([]);
    setCards({});
    setActiveApproval(null);
  }, []);

  return {
    status,
    messages,
    cards: Object.values(cards),
    activeApproval,
    setActiveApproval,
    sendMessage,
    sendApprovalDecision,
    triggerRun,
    resetBoard,
    wsUrl: url,
  };
}
