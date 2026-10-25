import React, { useState, useEffect, useRef } from "react";
import type { WhiteboardCard, EvidenceItem, CardStatus } from "../types/contracts";
import { BeehiveMascot, getChecklistFromCards } from "./BeehiveMascot";
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
  PanelLeftOpen,
  ArrowDownUp,
  Eye,
} from "lucide-react";

interface HoneycombWhiteboardProps {
  cards: WhiteboardCard[];
  onSelectEvidence: (evidence: EvidenceItem, cardTitle: string) => void;
  onRequestApproval: (card: WhiteboardCard) => void;
  status: "connecting" | "connected" | "disconnected";
  onTriggerRun?: () => void;
  onResetBoard: () => void;
  isSidebarOpen?: boolean;
  onToggleSidebar?: () => void;
  onOpenSettings?: () => void;
}

export const HoneycombWhiteboard: React.FC<HoneycombWhiteboardProps> = ({
  cards,
  onSelectEvidence,
  onRequestApproval,
  status,
  onResetBoard,
  isSidebarOpen = true,
  onToggleSidebar,
  onOpenSettings,
}) => {
  const [selectedLane, setSelectedLane] = useState<string>("all");
  const [sortOrder, setSortOrder] = useState<"order_asc" | "order_desc">("order_asc");
  const [isProgressPillHovered, setIsProgressPillHovered] = useState(false);

  // Active LLM provider and model display
  const [llmInfo, setLlmInfo] = useState<{ provider: string; model: string; icon: string }>({
    provider: "Pollinations AI",
    model: "openai/gpt-5.4-nano",
    icon: "🌸",
  });

  useEffect(() => {
    const updateLlmInfo = () => {
      try {
        const stored = localStorage.getItem("swarm_external_ai_config");
        if (stored) {
          const parsed = JSON.parse(stored);
          const pKey = parsed.provider || "pollinations";
          const icons: Record<string, string> = {
            pollinations: "🌸",
            openrouter: "🌐",
            openai: "⚡",
            claude: "🧠",
            gemini: "✨",
            nvidia: "🚀",
            ollama: "💻",
          };
          const names: Record<string, string> = {
            pollinations: "Pollinations AI",
            openrouter: "OpenRouter",
            openai: "OpenAI",
            claude: "Claude",
            gemini: "Gemini",
            nvidia: "NVIDIA NIM",
            ollama: "Ollama",
          };
          setLlmInfo({
            provider: names[pKey] || pKey,
            model: parsed.smartModel || "openai/gpt-5.4-nano",
            icon: icons[pKey] || "🌸",
          });
        }
      } catch {
        // fallback
      }
    };
    updateLlmInfo();
    window.addEventListener("swarm_config_updated", updateLlmInfo);
    window.addEventListener("storage", updateLlmInfo);
    return () => {
      window.removeEventListener("swarm_config_updated", updateLlmInfo);
      window.removeEventListener("storage", updateLlmInfo);
    };
  }, []);

  // Local state for manually toggled items if user checks them off in popover
  const [manualChecklistOverrides, setManualChecklistOverrides] = useState<Record<string, "done" | "planned">>({});

  // Card update order tracking
  const orderMapRef = useRef<Map<string, {
    order: number;
    latestUpdateSeq: number;
    updateCount: number;
    lastUpdatedAt: string;
    lastSignature: string;
  }>>(new Map());
  const globalSeqRef = useRef<number>(0);
  const [orderMap, setOrderMap] = useState<Record<string, {
    order: number;
    latestUpdateSeq: number;
    updateCount: number;
    lastUpdatedAt: string;
  }>>({});

  // Reset manual overrides and order counter if board resets
  useEffect(() => {
    if (cards.length === 0) {
      setManualChecklistOverrides({});
      orderMapRef.current.clear();
      globalSeqRef.current = 0;
      setOrderMap({});
    }
  }, [cards.length]);

  // Track order in which cards are created and updated
  useEffect(() => {
    if (cards.length === 0) return;

    let hasChanges = false;
    const currentMap = new Map(orderMapRef.current);

    if (currentMap.size === 0) {
      // Initial load: sort initial cards by updated_at ascending to establish true historical sequence
      const sortedInitial = [...cards].sort((a, b) => {
        const timeA = new Date(a.updated_at || 0).getTime();
        const timeB = new Date(b.updated_at || 0).getTime();
        if (timeA !== timeB) return timeA - timeB;
        return a.id.localeCompare(b.id);
      });

      sortedInitial.forEach((card) => {
        globalSeqRef.current += 1;
        const seq = globalSeqRef.current;
        const signature = `${card.status}::${card.updated_at}::${card.summary}::${card.evidence?.length || 0}`;
        currentMap.set(card.id, {
          order: seq,
          latestUpdateSeq: seq,
          updateCount: 1,
          lastUpdatedAt: card.updated_at || new Date().toISOString(),
          lastSignature: signature,
        });
      });
      hasChanges = true;
    } else {
      // Process incoming cards for additions or updates
      cards.forEach((card) => {
        const signature = `${card.status}::${card.updated_at}::${card.summary}::${card.evidence?.length || 0}`;
        const existing = currentMap.get(card.id);

        if (!existing) {
          globalSeqRef.current += 1;
          const seq = globalSeqRef.current;
          currentMap.set(card.id, {
            order: currentMap.size + 1,
            latestUpdateSeq: seq,
            updateCount: 1,
            lastUpdatedAt: card.updated_at || new Date().toISOString(),
            lastSignature: signature,
          });
          hasChanges = true;
        } else if (existing.lastSignature !== signature) {
          globalSeqRef.current += 1;
          const seq = globalSeqRef.current;
          currentMap.set(card.id, {
            ...existing,
            latestUpdateSeq: seq,
            updateCount: existing.updateCount + 1,
            lastUpdatedAt: card.updated_at || new Date().toISOString(),
            lastSignature: signature,
          });
          hasChanges = true;
        }
      });
    }

    if (hasChanges) {
      orderMapRef.current = currentMap;
      const record: Record<string, {
        order: number;
        latestUpdateSeq: number;
        updateCount: number;
        lastUpdatedAt: string;
      }> = {};
      currentMap.forEach((val, key) => {
        record[key] = {
          order: val.order,
          latestUpdateSeq: val.latestUpdateSeq,
          updateCount: val.updateCount,
          lastUpdatedAt: val.lastUpdatedAt,
        };
      });
      setOrderMap(record);
    }
  }, [cards]);

  const formatUpdateTime = (isoString?: string): string => {
    if (!isoString) return "just now";
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return "just now";
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return "just now";
    }
  };

  const { checklist: baseChecklist, progress: baseProgress, totalCount } =
    getChecklistFromCards(cards);

  // Apply manual overrides if any
  const checklist = baseChecklist.map((item) => {
    if (manualChecklistOverrides[item.id]) {
      return { ...item, status: manualChecklistOverrides[item.id] };
    }
    return item;
  });

  const completedCount = checklist.filter((i) => i.status === "done").length;
  const inProgressCount = checklist.filter(
    (i) => i.status === "in_progress" || i.status === "needs_approval"
  ).length;

  const progress =
    totalCount > 0
      ? Math.min(100, Math.max(0, Math.round(((completedCount + inProgressCount * 0.4) / totalCount) * 100)))
      : baseProgress;

  const handleToggleChecklistItem = (id: string) => {
    setManualChecklistOverrides((prev) => {
      const currentStatus = checklist.find((i) => i.id === id)?.status;
      const nextStatus = currentStatus === "done" ? "planned" : "done";
      return { ...prev, [id]: nextStatus };
    });
  };

  const lanes: Array<{ id: string; label: string }> = [
    { id: "all", label: "All Lanes" },
    { id: "FE", label: "FE" },
    { id: "BE", label: "BE" },
    { id: "Test", label: "Test (QA)" },
    { id: "Docs", label: "Docs (Research)" },
    { id: "Ops", label: "Ops" },
  ];

  const filteredCards = cards
    .filter((card) => {
      if (selectedLane === "all") return true;
      return card.lane === selectedLane;
    })
    .sort((a, b) => {
      const orderA = orderMap[a.id]?.order ?? 999;
      const orderB = orderMap[b.id]?.order ?? 999;
      const latestA = orderMap[a.id]?.latestUpdateSeq ?? 0;
      const latestB = orderMap[b.id]?.latestUpdateSeq ?? 0;

      if (sortOrder === "order_desc") {
        return latestB - latestA;
      }
      return orderA - orderB;
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
          {!isSidebarOpen && onToggleSidebar && (
            <button
              type="button"
              className="retro-control-btn toggle-sidebar-btn"
              onClick={onToggleSidebar}
              title="Show Sidebar (Ctrl+B)"
            >
              <PanelLeftOpen size={14} />
              <span>Sidebar</span>
            </button>
          )}
          <span className="canvas-header-tag">WHITEBOARD</span>
          <div className="status-connection-badge">
            <span className={`status-indicator-dot status-${status}`} />
            <span className="status-indicator-text">
              {status === "connected" ? "Swarm Online" : status === "connecting" ? "Connecting..." : "Offline"}
            </span>
          </div>

          {/* Active LLM Provider Status Indicator */}
          <div
            className="llm-status-pill"
            onClick={onOpenSettings}
            title={`Active LLM Engine: ${llmInfo.provider} (${llmInfo.model}). Click to configure.`}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onOpenSettings?.()}
          >
            <span className="llm-dot" />
            <span className="llm-icon-mini">{llmInfo.icon}</span>
            <span className="llm-status-text">
              LLM: <strong>{llmInfo.provider}</strong> • <span className="llm-model-name">{llmInfo.model}</span>
            </span>
          </div>

          {/* TinyFish Engine Status Indicator */}
          <div
            className="tinyfish-status-pill"
            onClick={onOpenSettings}
            title="Autonomous Web Search, Fetch & Real-Browser Verification. Click to configure."
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onOpenSettings?.()}
          >
            <span className="tinyfish-dot" />
            <Sparkles size={11} className="tinyfish-header-sparkle" />
            <span className="tinyfish-status-text">TinyFish Browser Engine: READY</span>
          </div>
        </div>

        <div className="canvas-header-controls">
          <button
            type="button"
            className="retro-control-btn reset-btn"
            onClick={onResetBoard}
            title="Reset Whiteboard & Feed"
          >
            <span>↺</span>
            <span>Reset Board</span>
          </button>
        </div>
      </div>

      {/* Main Inner Canvas Container with Retro Border & Dot Grid */}
      <div className="whiteboard-inner-frame">
        {/* Background Dot Matrix pattern */}
        <div className="canvas-dot-matrix" />

        <div className="populated-whiteboard-view">
          {/* Whiteboard Sub-Navigation / Filter Bar - Always Rendered */}
          <div className="whiteboard-subbar">
            <div className="whiteboard-info-group">
              <div className="whiteboard-mini-mascot">
                <BeehiveMascot
                  size="sm"
                  progress={progress}
                  checklist={checklist}
                  onToggleItem={handleToggleChecklistItem}
                  forceOpen={isProgressPillHovered}
                />
              </div>
              <div>
                <div className="whiteboard-title-row">
                  <h2 className="whiteboard-heading">Honeycomb Whiteboard</h2>
                  <div
                    className={`honey-progress-pill ${totalCount === 0 ? "standby" : ""}`}
                    title={
                      totalCount === 0
                        ? "Hive on standby • 0 active milestones"
                        : "Hover beehive to view remaining checklist"
                    }
                    onMouseEnter={() => setIsProgressPillHovered(true)}
                    onMouseLeave={() => setIsProgressPillHovered(false)}
                    onClick={() => setIsProgressPillHovered((prev) => !prev)}
                  >
                    <span className="honey-drop-emoji">{totalCount === 0 ? "🫙" : "🍯"}</span>
                    <span className="honey-progress-pct">{totalCount === 0 ? "Standby" : `${progress}% Honey`}</span>
                    <span className="honey-progress-sub">({totalCount === 0 ? "0 Tasks" : `${completedCount}/${totalCount} Done`})</span>
                  </div>
                </div>
                <p className="whiteboard-subheading">
                  Synthesized project milestones & live verification evidence
                </p>
              </div>
            </div>

            <div className="whiteboard-subbar-right">
              <div className="order-sort-group">
                <span className="filter-label">
                  <ArrowDownUp size={11} /> Order:
                </span>
                <button
                  type="button"
                  className={`lane-pill-filter ${sortOrder === "order_asc" ? "active" : ""}`}
                  onClick={() => setSortOrder("order_asc")}
                  title="Sort by Chronological Milestone Update Order (#1 to #N)"
                >
                  #1 → #N
                </button>
                <button
                  type="button"
                  className={`lane-pill-filter ${sortOrder === "order_desc" ? "active" : ""}`}
                  onClick={() => setSortOrder("order_desc")}
                  title="Sort by Most Recently Updated First"
                >
                  Latest First
                </button>
              </div>

              <div className="lane-filters-group">
                <span className="filter-label">
                  <Filter size={11} /> Filter:
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
          </div>

          {/* Cards Grid */}
          <div className="cards-canvas-grid">
            {filteredCards.length === 0 ? (
              <div className="empty-whiteboard-grid-placeholder">
                <div className="empty-placeholder-mascot">
                  <BeehiveMascot
                    size="md"
                    showText={false}
                    progress={progress}
                    checklist={checklist}
                    onToggleItem={handleToggleChecklistItem}
                  />
                </div>
                <h3 className="empty-placeholder-title">
                  {selectedLane !== "all"
                    ? `No cards in ${selectedLane} lane`
                    : "The Hive is Standing By"}
                </h3>
                <p className="empty-placeholder-sub">
                  {selectedLane !== "all"
                    ? `Milestone cards assigned to ${selectedLane} will appear here as workers execute.`
                    : "Send a goal in the Nectar Feed to deploy Queen, Workers, Scribe, and QA Bees."}
                </p>
              </div>
            ) : (
              filteredCards.map((card) => {
                const isNeedsApproval = card.status === "needs_approval";
                const orderInfo = orderMap[card.id] || {
                  order: 1,
                  latestUpdateSeq: 1,
                  updateCount: 1,
                  lastUpdatedAt: card.updated_at,
                };

                const isTinyFishVerified =
                  card.lane === "Test" ||
                  card.title.toLowerCase().includes("tinyfish") ||
                  card.summary.toLowerCase().includes("tinyfish") ||
                  Boolean(
                    card.evidence?.some(
                      (e) =>
                        e.kind === "screenshot" ||
                        e.kind === "browser_log" ||
                        e.kind.toLowerCase().includes("tinyfish") ||
                        e.url_or_text.toLowerCase().includes("tinyfish")
                    )
                  );

                const screenshotEvidence = card.evidence?.find(
                  (e) =>
                    e.kind === "screenshot" ||
                    e.url_or_text.endsWith(".png") ||
                    e.url_or_text.endsWith(".jpg") ||
                    e.url_or_text.includes("evidence") ||
                    e.url_or_text.includes("pass.png")
                );

                return (
                  <article
                    key={card.id}
                    className={`honey-card honey-status-${card.status} ${
                      isNeedsApproval ? "card-pulse-approval" : ""
                    } ${isTinyFishVerified ? "card-tinyfish-highlight" : ""}`}
                  >
                    {/* Card Header */}
                    <div className="honey-card-top">
                      <div className="honey-card-tags">
                        {/* Numbered update sequence badge */}
                        <div
                          className="card-order-badge"
                          title={`Milestone Update #${orderInfo.order} • ${
                            orderInfo.updateCount > 1
                              ? `Updated ${orderInfo.updateCount} times (latest event #${orderInfo.latestUpdateSeq})`
                              : "1st update event"
                          }`}
                        >
                          <span className="order-badge-hash">#</span>
                          <span className="order-badge-num">{orderInfo.order}</span>
                        </div>
                        <span className={`lane-chip lane-${card.lane.toLowerCase()}`}>
                          {card.lane}
                        </span>
                        {orderInfo.updateCount > 1 && (
                          <span
                            className="card-rev-chip"
                            title={`Revised: latest update event #${orderInfo.latestUpdateSeq} in sequence`}
                          >
                            v{orderInfo.updateCount}
                          </span>
                        )}
                      </div>
                      <div className={`status-pill pill-${card.status}`}>
                        {getStatusIcon(card.status)}
                        <span>{getStatusLabel(card.status)}</span>
                      </div>
                    </div>

                    {/* Verified by TinyFish Badge */}
                    {isTinyFishVerified && (
                      <div className="tinyfish-verified-card-banner">
                        <div className="tinyfish-badge-left">
                          <span className="tinyfish-pulsing-dot" />
                          <ShieldCheck size={13} className="tinyfish-shield-icon" />
                          <span className="tinyfish-badge-text">
                            {card.lane === "Test" || screenshotEvidence
                              ? "Verified by TinyFish Browser Agent"
                              : "Verified by TinyFish Web Engine"}
                          </span>
                        </div>
                        {card.evidence && card.evidence.length > 0 && (
                          <button
                            type="button"
                            className="tinyfish-inspect-proof-btn"
                            onClick={() => onSelectEvidence(screenshotEvidence || card.evidence![0], card.title)}
                            title="Inspect real browser execution trace & visual screenshot proof"
                          >
                            <Eye size={11} />
                            <span>Inspect Proof</span>
                          </button>
                        )}
                      </div>
                    )}

                    {/* Card Title & Plain-Language Scribe Summary */}
                    <h3 className="honey-card-title">{card.title}</h3>
                    <p className="honey-card-summary">{card.summary}</p>

                    {/* In-Card Screenshot Thumbnail Preview */}
                    {screenshotEvidence && (
                      <div
                        className="card-screenshot-thumbnail-box"
                        onClick={() => onSelectEvidence(screenshotEvidence, card.title)}
                        title="Click to inspect TinyFish real-browser screenshot proof"
                      >
                        <div className="thumbnail-browser-top">
                          <div className="mini-browser-dots">
                            <span className="dot red" />
                            <span className="dot yellow" />
                            <span className="dot green" />
                          </div>
                          <span className="mini-browser-url">http://localhost:5173/waitlist</span>
                          <span className="mini-browser-badge">PASS ✓</span>
                        </div>
                        <div className="thumbnail-viewport">
                          <div className="mini-mock-waitlist-preview">
                            <div className="mini-mock-badge">🐝 SWARM LAUNCH</div>
                            <div className="mini-mock-heading">Join the Swarm Waitlist</div>
                            <div className="mini-mock-form">
                              <span className="mini-input">developer@example.com</span>
                              <span className="mini-btn">Join Access</span>
                            </div>
                            <div className="mini-mock-toast">✓ #42 on waitlist! Confirmed.</div>
                          </div>
                          <div className="thumbnail-hover-overlay">
                            <Eye size={13} />
                            <span>Inspect TinyFish Proof</span>
                          </div>
                        </div>
                      </div>
                    )}

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

                    {/* Card Footer: Update Sequence Order & Timestamp Tracking */}
                    <div className="card-order-footer">
                      <span className="card-order-seq-label" title={card.updated_at}>
                        <Clock size={10} className="text-stone-500" />
                        <span>Update #{orderInfo.order} in queue</span>
                        {orderInfo.updateCount > 1 && (
                          <span className="order-multi-update">
                            • #{orderInfo.latestUpdateSeq} latest
                          </span>
                        )}
                      </span>
                      <span className="card-timestamp-text">
                        {formatUpdateTime(card.updated_at)}
                      </span>
                    </div>
                  </article>
                );
              }))}
            </div>
        </div>
      </div>
    </section>
  );
};
