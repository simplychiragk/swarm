import React, { useEffect, useState, useRef } from "react";
import type {
  EventEnvelope,
  FeedMessage,
  WhiteboardCard,
  ApprovalRequest,
} from "./types/contracts";
import "./App.css";

const DEFAULT_WS_URL = "ws://127.0.0.1:8000/ws";

export function App() {
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const [messages, setMessages] = useState<FeedMessage[]>([]);
  const [cards, setCards] = useState<Record<string, WhiteboardCard>>({});
  const [activeApproval, setActiveApproval] = useState<ApprovalRequest | null>(null);
  const [userInput, setUserInput] = useState<string>("");

  const socketRef = useRef<WebSocket | null>(null);
  const feedEndRef = useRef<HTMLDivElement | null>(null);

  const connect = () => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    setStatus("connecting");
    try {
      const ws = new WebSocket(DEFAULT_WS_URL);

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data) as EventEnvelope;
          if (envelope.event === "feed_message") {
            setMessages((prev) => [...prev, envelope.payload]);
          } else if (envelope.event === "card_upsert") {
            setCards((prev) => ({
              ...prev,
              [envelope.payload.id]: envelope.payload,
            }));
          } else if (envelope.event === "approval_request") {
            setActiveApproval(envelope.payload);
          }
        } catch (err) {
          console.error("Failed to parse event:", err);
        }
      };

      ws.onclose = () => setStatus("disconnected");
      ws.onerror = () => setStatus("disconnected");

      socketRef.current = ws;
    } catch (e) {
      console.error("WebSocket init error:", e);
      setStatus("disconnected");
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim() || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const payload = {
      id: `user-msg-${Date.now()}`,
      text: userInput.trim(),
      timestamp: new Date().toISOString(),
    };

    socketRef.current.send(
      JSON.stringify({
        event: "user_message",
        payload,
      })
    );

    // Also optimistically add to local feed as user message
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

    setUserInput("");
  };

  const handleApprovalDecision = (decision: "approve" | "redirect") => {
    if (!activeApproval || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    socketRef.current.send(
      JSON.stringify({
        event: "approval_response",
        payload: {
          approval_id: activeApproval.id,
          card_id: activeApproval.card_id,
          decision,
          note: decision === "approve" ? "Approved by user" : "Redirected by user",
        },
      })
    );

    setActiveApproval(null);
  };

  const handleTriggerRun = async () => {
    try {
      await fetch("http://127.0.0.1:8000/mock/start", { method: "POST" });
    } catch (e) {
      console.error("Trigger error:", e);
    }
  };

  const handleResetBoard = async () => {
    try {
      await fetch("http://127.0.0.1:8000/mock/reset", { method: "POST" });
      setMessages([]);
      setCards({});
      setActiveApproval(null);
    } catch (e) {
      console.error("Reset error:", e);
    }
  };

  const cardList = Object.values(cards);

  return (
    <div className="app-shell">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section">
          <span className="brand-icon" role="img" aria-label="bee">
            🐝
          </span>
          <div>
            <h1 className="brand-title">Swarm</h1>
          </div>
          <span className="brand-subtitle">Honeycomb Workspace</span>
        </div>

        <div className="header-status-group">
          <div className={`status-pill status-${status}`}>
            <span className="status-dot" aria-hidden="true" />
            <span>{status.toUpperCase()}</span>
          </div>

          <button onClick={handleTriggerRun} className="btn btn-primary" type="button">
            ▶ Run Demo Scenario
          </button>
          <button onClick={handleResetBoard} className="btn btn-secondary" type="button">
            ↺ Reset
          </button>
        </div>
      </header>

      {/* Main Two-Column View */}
      <main className="app-main">
        {/* Left Column: Live Agent Chatter Feed (Nectar) */}
        <aside className="feed-aside" aria-label="Agent Chat Feed">
          <header className="feed-header">
            <h2>Nectar Feed ({messages.length})</h2>
          </header>

          <div className="feed-scroll-area">
            {messages.length === 0 ? (
              <p style={{ color: "var(--color-text-dim)", fontSize: "12px", textAlign: "center", marginTop: "32px" }}>
                Waiting for agent chatter... Click "Run Demo Scenario" above.
              </p>
            ) : (
              messages.map((m) => {
                const senderClass = `badge-${m.sender}`;
                return (
                  <article key={m.id} className="feed-msg-item">
                    <header className="feed-msg-meta">
                      <span className={`agent-badge ${senderClass}`}>
                        {m.sender === "queen" && "👑 Queen"}
                        {m.sender === "worker" && "⚙️ Worker"}
                        {m.sender === "scribe" && "📜 Scribe"}
                        {m.sender === "qa" && "🧪 QA Bee"}
                        {m.sender === "research" && "🔍 Research Bee"}
                        {m.sender === "system" && "👤 System / User"}
                      </span>
                      {m.lane !== "none" && <span className="lane-tag">{m.lane}</span>}
                    </header>
                    <p className="feed-msg-body">{m.content}</p>
                  </article>
                );
              })
            )}
            <div ref={feedEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="feed-input-bar">
            <input
              type="text"
              className="feed-input"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="Send instruction or answer to Queen..."
              aria-label="User input message"
            />
            <button type="submit" className="btn btn-primary">
              Send
            </button>
          </form>
        </aside>

        {/* Right Column: Honeycomb Whiteboard (Honey) */}
        <section className="board-section" aria-label="Honeycomb Whiteboard">
          {/* Active Approval Banner if flagged */}
          {activeApproval && (
            <section className="approval-banner" aria-label="Approval Gate">
              <header className="approval-banner-header">
                <span className="approval-icon" role="img" aria-label="shield">
                  🛡️
                </span>
                <h3 className="approval-title">Decision Layer: User Approval Required</h3>
              </header>
              <p className="approval-prompt">{activeApproval.prompt}</p>
              <div className="approval-actions">
                <button
                  type="button"
                  onClick={() => handleApprovalDecision("approve")}
                  className="btn btn-approve"
                >
                  ✓ Approve & Deploy Live
                </button>
                <button
                  type="button"
                  onClick={() => handleApprovalDecision("redirect")}
                  className="btn btn-redirect"
                >
                  ✕ Request Revision
                </button>
              </div>
            </section>
          )}

          <header className="board-header">
            <div className="board-title-group">
              <h2>Honeycomb Whiteboard</h2>
              <p>Clean plain-language milestone summaries curated by the Scribe Bee</p>
            </div>
            <span style={{ fontSize: "12px", color: "var(--color-text-dim)" }}>
              {cardList.length} card(s) active
            </span>
          </header>

          <div className="cards-grid">
            {cardList.length === 0 ? (
              <div style={{ gridColumn: "1 / -1", textAlign: "center", padding: "64px 16px", color: "var(--color-text-dim)" }}>
                <p style={{ fontSize: "14px" }}>No cards on the whiteboard yet.</p>
                <p style={{ fontSize: "12px", marginTop: "8px" }}>
                  When agents complete discovery and tasks, Scribe posts honey cards here.
                </p>
              </div>
            ) : (
              cardList.map((card) => {
                const statusClass = `card-status-${card.status}`;
                const pillClass = `pill-${card.status}`;
                return (
                  <article key={card.id} className={`whiteboard-card ${statusClass}`}>
                    <header className="card-top">
                      <span className="card-lane-badge">{card.lane}</span>
                      <span className={`card-status-pill ${pillClass}`}>
                        {card.status.replace("_", " ")}
                      </span>
                    </header>

                    <h3 className="card-title">{card.title}</h3>
                    <p className="card-summary">{card.summary}</p>

                    {card.evidence && card.evidence.length > 0 && (
                      <footer className="evidence-container">
                        <span style={{ fontSize: "10px", color: "var(--color-text-dim)", textTransform: "uppercase", fontWeight: 700 }}>
                          Verified Evidence:
                        </span>
                        {card.evidence.map((item, idx) => (
                          <span key={idx} className="evidence-tag">
                            {item.kind === "screenshot" && "📸 Screenshot: "}
                            {item.kind === "tinyfish_search" && "🔍 TinyFish: "}
                            {item.kind === "browser_log" && "🧪 Assertion: "}
                            {item.kind !== "screenshot" && item.kind !== "tinyfish_search" && item.kind !== "browser_log" && "📎 "}
                            {item.url_or_text}
                          </span>
                        ))}
                      </footer>
                    )}
                  </article>
                );
              })
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
