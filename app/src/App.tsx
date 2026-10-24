import React, { useEffect, useState, useRef } from "react";
import type { EventEnvelope } from "./types/contracts";
import "./App.css";

const DEFAULT_WS_URL = "ws://localhost:8000/ws";

interface ReceivedEvent {
  receivedAt: string;
  data: EventEnvelope;
}

export function App() {
  const [wsUrl, setWsUrl] = useState<string>(DEFAULT_WS_URL);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const [events, setEvents] = useState<ReceivedEvent[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  const connect = (url: string) => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    setStatus("connecting");
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as EventEnvelope;
          setEvents((prev) => [
            {
              receivedAt: new Date().toLocaleTimeString(),
              data: parsed,
            },
            ...prev,
          ]);
        } catch (err) {
          console.error("Failed to parse WebSocket event:", err, event.data);
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        setStatus("disconnected");
      };

      socketRef.current = ws;
    } catch (e) {
      console.error("Error creating WebSocket:", e);
      setStatus("disconnected");
    }
  };

  useEffect(() => {
    connect(wsUrl);
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  const handleReconnect = (e: React.FormEvent) => {
    e.preventDefault();
    connect(wsUrl);
  };

  const handleClear = () => {
    setEvents([]);
  };

  return (
    <main className="swarm-container">
      <header className="swarm-header">
        <div className="swarm-title-group">
          <h1>Swarm Contract Debug Shell</h1>
          <p>Listening to sidecar WebSocket stream & printing raw EventEnvelope payloads</p>
        </div>

        <div className={`status-badge status-${status}`}>
          <span className="status-dot" aria-hidden="true" />
          <span>{status.toUpperCase()}</span>
        </div>
      </header>

      <section aria-label="Connection controls" className="swarm-controls">
        <form onSubmit={handleReconnect} style={{ display: "flex", gap: "8px" }}>
          <input
            type="text"
            className="swarm-input"
            value={wsUrl}
            onChange={(e) => setWsUrl(e.target.value)}
            aria-label="WebSocket URL"
            placeholder="ws://localhost:8000/ws"
          />
          <button type="submit" className="swarm-btn">
            Connect
          </button>
        </form>
        <button type="button" onClick={handleClear} className="swarm-btn swarm-btn-secondary">
          Clear Events ({events.length})
        </button>
      </section>

      <section aria-label="Event Stream" className="events-section">
        <header className="events-header">
          <h2>Live Streamed Events</h2>
          <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Showing {events.length} event(s)
          </span>
        </header>

        {events.length === 0 ? (
          <div className="empty-state">
            <p>Waiting for events from sidecar at <code>{wsUrl}</code>...</p>
            <p style={{ marginTop: "8px", fontSize: "12px" }}>
              Make sure the sidecar is running (<code>python -m uvicorn sidecar.main:app --port 8000</code>).
            </p>
          </div>
        ) : (
          <div className="events-list">
            {events.map((evt, idx) => {
              const eventType = evt.data.event;
              return (
                <article key={`${evt.receivedAt}-${idx}`} className="event-card">
                  <header className="event-card-header">
                    <span className={`event-type-tag event-type-${eventType}`}>
                      {eventType}
                    </span>
                    <time dateTime={evt.receivedAt}>{evt.receivedAt}</time>
                  </header>
                  <pre className="event-raw-json">
                    {JSON.stringify(evt.data, null, 2)}
                  </pre>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
