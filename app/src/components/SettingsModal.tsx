import React, { useState } from "react";
import { X, Wrench, Radio, Key, Users, CheckCircle2 } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: "connecting" | "connected" | "disconnected";
  wsUrl: string;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  status,
  wsUrl,
}) => {
  const [apiKey, setApiKey] = useState("tf_live_********************");
  const [swarmMode, setSwarmMode] = useState<"mock" | "live">("mock");

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="settings-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
      >
        <div className="settings-header">
          <div className="settings-title-group">
            <Wrench size={18} className="settings-icon" />
            <div>
              <h3 id="settings-title" className="settings-title">
                Swarm Configuration & Runtime
              </h3>
              <p className="settings-subtitle">HackIIITD 2026 • Esya '26 Final</p>
            </div>
          </div>
          <button type="button" className="retro-icon-btn" onClick={onClose} aria-label="Close settings">
            <X size={16} />
          </button>
        </div>

        <div className="settings-body">
          {/* Sidecar Connection */}
          <div className="settings-section">
            <h4 className="section-label">
              <Radio size={14} /> Sidecar WebSocket Connection
            </h4>
            <div className="connection-info-row">
              <span className="mono-code">{wsUrl}</span>
              <span className={`status-pill pill-${status}`}>
                {status.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Swarm Mode */}
          <div className="settings-section">
            <h4 className="section-label">
              <Radio size={14} /> Swarm Execution Mode
            </h4>
            <div className="mode-toggle-group">
              <button
                type="button"
                className={`mode-btn ${swarmMode === "mock" ? "active" : ""}`}
                onClick={() => setSwarmMode("mock")}
              >
                Mock Scenario (Section 9)
              </button>
              <button
                type="button"
                className={`mode-btn ${swarmMode === "live" ? "active" : ""}`}
                onClick={() => setSwarmMode("live")}
              >
                Live Multi-Agent Run
              </button>
            </div>
            <p className="section-hint">
              Mock scenario exercises the full pipeline: Queen interview, TinyFish search, FE/BE builds, Scribe summaries, TinyFish browser QA, and User approval gate.
            </p>
          </div>

          {/* TinyFish API Configuration */}
          <div className="settings-section">
            <h4 className="section-label">
              <Key size={14} /> TinyFish Web Automation & QA
            </h4>
            <div className="input-with-badge">
              <input
                type="password"
                className="retro-input"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter TinyFish API Key"
              />
              <span className="tinyfish-verified-chip">
                <CheckCircle2 size={12} /> Ready
              </span>
            </div>
            <p className="section-hint">
              Powers live research search/fetch & QA automated browser verification tests.
            </p>
          </div>

          {/* Swarm Agents Roster */}
          <div className="settings-section">
            <h4 className="section-label">
              <Users size={14} /> Active Swarm Agents
            </h4>
            <div className="agent-roster-grid">
              <div className="roster-item">
                <span className="roster-emoji">👑</span>
                <div>
                  <strong>Queen Bee</strong>
                  <p>Planner, Interviewer & Delegator</p>
                </div>
              </div>
              <div className="roster-item">
                <span className="roster-emoji">📜</span>
                <div>
                  <strong>Scribe Bee</strong>
                  <p>Whiteboard Honey Summaries</p>
                </div>
              </div>
              <div className="roster-item">
                <span className="roster-emoji">🔍</span>
                <div>
                  <strong>Research Bee</strong>
                  <p>TinyFish Search & Fresh Web Docs</p>
                </div>
              </div>
              <div className="roster-item">
                <span className="roster-emoji">🧪</span>
                <div>
                  <strong>QA Bee</strong>
                  <p>TinyFish Browser Test & Evidence</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="settings-footer">
          <button type="button" className="retro-btn retro-btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
