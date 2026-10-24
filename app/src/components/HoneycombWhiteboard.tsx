import React, { useState } from "react";
import type { WhiteboardCard, EvidenceItem, CardStatus } from "../types/contracts";
import { BeehiveMascot } from "./BeehiveMascot";
import {
  Sparkles,
  CheckCircle,
  Clock,
  Activity,
  AlertTriangle,
  XCircle,
  ExternalLink,
  ShieldCheck,
  Filter,
} from "lucide-react";

interface HoneycombWhiteboardProps {
  cards: WhiteboardCard[];
  onSelectEvidence: (evidence: EvidenceItem, cardTitle: string) => void;
  onRequestApproval: (card: WhiteboardCard) => void;
  status: "connecting" | "connected" | "disconnected";
  onTriggerRun: () => void;
  onResetBoard: () => void;
}

export const HoneycombWhiteboard: React.FC<HoneycombWhiteboardProps> = ({
  cards,
  onSelectEvidence,
  onRequestApproval,
  status,
  onTriggerRun,
  onResetBoard,
}) => {
  const [selectedLane, setSelectedLane] = useState<string>("all");

  const lanes: Array<{ id: string; label: string }> = [
    { id: "all", label: "All Lanes" },
    { id: "FE", label: "FE" },
    { id: "BE", label: "BE" },
    { id: "Test", label: "Test (QA)" },
    { id: "Docs", label: "Docs (Research)" },
    { id: "Ops", label: "Ops" },
  ];

  const filteredCards = cards.filter((card) => {
    if (selectedLane === "all") return true;
    return card.lane === selectedLane;
  });

  const getStatusIcon = (cardStatus: CardStatus) => {
    switch (cardStatus) {
      case "done":
        return <CheckCircle size={13} className="text-emerald-700" />;
      case "in_progress":
        return <Activity size={13} className="text-amber-700 animate-spin-slow" />;
      case "needs_approval":
        return <AlertTriangle size={13} className="text-amber-600 animate-pulse" />;
      case "failed":
        return <XCircle size={13} className="text-rose-600" />;
      case "planned":
      default:
        return <Clock size={13} className="text-stone-500" />;
    }
  };

  const getStatusLabel = (cardStatus: CardStatus) => {
    switch (cardStatus) {
      case "in_progress":
        return "In Progress";
      case "needs_approval":
        return "Needs Approval";
      case "done":
        return "Done";
      case "failed":
        return "Failed";
      case "planned":
      default:
        return "Planned";
    }
  };

  return (
    <section className="whiteboard-canvas-wrapper" aria-label="Honeycomb Whiteboard Canvas">
      {/* Canvas Top Bar */}
      <div className="canvas-header-bar">
        <div className="canvas-header-left">
          <span className="canvas-header-tag">WHITEBOARD</span>
          <div className="status-connection-badge">
            <span className={`status-indicator-dot status-${status}`} />
            <span className="status-indicator-text">
              {status === "connected" ? "Swarm Online" : status === "connecting" ? "Connecting..." : "Offline"}
            </span>
          </div>
        </div>

        <div className="canvas-header-controls">
          <button
            type="button"
            className="retro-control-btn primary-run-btn"
            onClick={onTriggerRun}
            title="Trigger Section 9 Waitlist Landing Page Scenario"
          >
            <span className="play-icon">▶</span>
            <span>Run Demo</span>
          </button>
          <button
            type="button"
            className="retro-control-btn reset-btn"
            onClick={onResetBoard}
            title="Reset Board & Feed"
          >
            <span>↺</span>
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Main Inner Canvas Container with Retro Border & Dot Grid */}
      <div className="whiteboard-inner-frame">
        {/* Background Dot Matrix pattern */}
        <div className="canvas-dot-matrix" />

        {/* Bottom-right decorative dot cluster & Sparkle Star (matches design) */}
        <div className="canvas-corner-accent">
          <div className="corner-dot-cluster" />
          <div className="corner-sparkle-star">
            <Sparkles size={24} strokeWidth={1.8} />
          </div>
        </div>

        {cards.length === 0 ? (
          /* Empty State - Exact Match to Uploaded Design */
          <div className="empty-whiteboard-view">
            <BeehiveMascot size="lg" showText />
          </div>
        ) : (
          /* Populated State - Honeycomb Milestone Cards */
          <div className="populated-whiteboard-view">
            {/* Whiteboard Sub-Navigation / Filter Bar */}
            <div className="whiteboard-subbar">
              <div className="whiteboard-info-group">
                <div className="whiteboard-mini-mascot">
                  <BeehiveMascot size="sm" />
                </div>
                <div>
                  <h2 className="whiteboard-heading">Honeycomb Whiteboard</h2>
                  <p className="whiteboard-subheading">
                    Synthesized project milestones & live verification evidence
                  </p>
                </div>
              </div>

              <div className="lane-filters-group">
                <span className="filter-label">
                  <Filter size={12} /> Filter:
                </span>
                {lanes.map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    className={`lane-pill-filter ${selectedLane === l.id ? "active" : ""}`}
                    onClick={() => setSelectedLane(l.id)}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Cards Grid */}
            <div className="cards-canvas-grid">
              {filteredCards.map((card) => {
                const isNeedsApproval = card.status === "needs_approval";
                return (
                  <article
                    key={card.id}
                    className={`honey-card honey-status-${card.status} ${
                      isNeedsApproval ? "card-pulse-approval" : ""
                    }`}
                  >
                    {/* Card Header */}
                    <div className="honey-card-top">
                      <div className="honey-card-tags">
                        <span className={`lane-chip lane-${card.lane.toLowerCase()}`}>
                          {card.lane}
                        </span>
                      </div>
                      <div className={`status-pill pill-${card.status}`}>
                        {getStatusIcon(card.status)}
                        <span>{getStatusLabel(card.status)}</span>
                      </div>
                    </div>

                    {/* Card Title & Plain-Language Scribe Summary */}
                    <h3 className="honey-card-title">{card.title}</h3>
                    <p className="honey-card-summary">{card.summary}</p>

                    {/* Verified Evidence Attachments */}
                    {card.evidence && card.evidence.length > 0 && (
                      <div className="honey-evidence-tray">
                        <div className="evidence-tray-label">
                          <Sparkles size={11} />
                          <span>TinyFish Evidence:</span>
                        </div>
                        <div className="evidence-items-list">
                          {card.evidence.map((item, idx) => (
                            <button
                              key={idx}
                              type="button"
                              className="evidence-item-btn"
                              onClick={() => onSelectEvidence(item, card.title)}
                              title={`Inspect evidence: ${item.url_or_text}`}
                            >
                              <span className="evidence-kind-tag">{item.kind}</span>
                              <span className="evidence-text-preview">{item.url_or_text}</span>
                              <ExternalLink size={11} className="evidence-ext-icon" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Interactive Approval Gate Banner if status is needs_approval */}
                    {isNeedsApproval && (
                      <div className="card-action-footer">
                        <button
                          type="button"
                          className="retro-approval-action-btn"
                          onClick={() => onRequestApproval(card)}
                        >
                          <ShieldCheck size={14} />
                          <span>Review Approval Gate</span>
                        </button>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
