import { useState, useEffect, useRef, useCallback } from "react";
import type {
  EventEnvelope,
  FeedMessage,
  WhiteboardCard,
  ApprovalRequest,
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
  const cardsRef = useRef<Record<string, WhiteboardCard>>({});

  const connect = useCallback(() => {
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
            setCards({ ...cardsRef.current });

            // If a card update arrives marking the card done/failed, dismiss any pending approval for it
            setActiveApproval((currentAppr) => {
              if (currentAppr && currentAppr.card_id === card.id && (card.status === "done" || card.status === "failed")) {
                return null;
              }
              return currentAppr;
            });
          } else if (envelope.event === "approval_request") {
            const req = envelope.payload;
            const existingCard = cardsRef.current[req.card_id];
            // Only display modal if card is not already done or failed
            if (!existingCard || (existingCard.status !== "done" && existingCard.status !== "failed")) {
              setActiveApproval(req);
            }
          }
        } catch (err) {
          console.error("Failed to parse WebSocket event:", err);
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        // Only reconnect if disconnect was NOT intentional
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

      const payload = {
        approval_id: activeApproval.id,
        card_id: activeApproval.card_id,
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

      // Optimistically update card status locally
      const updatedStatus = decision === "approve" ? "done" : "failed";
      const target = cardsRef.current[activeApproval.card_id];
      if (target) {
        cardsRef.current[activeApproval.card_id] = {
          ...target,
          status: updatedStatus,
          summary:
            decision === "approve"
              ? "Production release authorized by user. Live."
              : `Release redirected: ${payload.note}`,
        };
        setCards({ ...cardsRef.current });
      }

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
