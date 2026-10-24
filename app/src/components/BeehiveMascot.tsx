import React, { useState, useRef, useId } from "react";
import type { WhiteboardCard } from "../types/contracts";
import {
  CheckCircle,
  Clock,
  Activity,
  AlertTriangle,
  Sparkles,
  Check,
} from "lucide-react";

export interface ChecklistItem {
  id: string;
  title: string;
  summary: string;
  lane?: string;
  status: "done" | "in_progress" | "needs_approval" | "planned" | "failed";
}

export const DEFAULT_SWARM_MILESTONES: ChecklistItem[] = [
  {
    id: "discovery",
    title: "Discovery & Goal Definition",
    summary: "Queen interviews user to lock specs: target audience, design theme, form fields",
    lane: "Queen",
    status: "planned",
  },
  {
    id: "research",
    title: "Live Web Research (TinyFish)",
    summary: "Query TinyFish for modern 2026 React form patterns & waitlist best practices",
    lane: "Docs",
    status: "planned",
  },
  {
    id: "frontend",
    title: "Frontend Component Architecture",
    summary: "FE worker generates responsive Tailwind & React waitlist landing page",
    lane: "FE",
    status: "planned",
  },
  {
    id: "backend",
    title: "Backend API & Storage Contract",
    summary: "BE worker implements SQLite waitlist storage and REST endpoints",
    lane: "BE",
    status: "planned",
  },
  {
    id: "qa",
    title: "Automated Real-Browser QA",
    summary: "QA bee submits waitlist form in headless Chromium & captures evidence",
    lane: "Test",
    status: "planned",
  },
  {
    id: "deploy",
    title: "Decision Layer Authorization",
    summary: "Jev rule engine gate requiring human authorization to deploy live changes",
    lane: "Ops",
    status: "planned",
  },
];

export function getChecklistFromCards(cards: WhiteboardCard[]): {
  checklist: ChecklistItem[];
  progress: number;
  completedCount: number;
  totalCount: number;
} {
  if (!cards || cards.length === 0) {
    return {
      checklist: DEFAULT_SWARM_MILESTONES,
      progress: 0,
      completedCount: 0,
      totalCount: DEFAULT_SWARM_MILESTONES.length,
    };
  }

  const cardMap = new Map<string, WhiteboardCard>();
  cards.forEach((c) => {
    cardMap.set(c.id, c);
  });

  const matchedIds = new Set<string>();
  const checklist: ChecklistItem[] = [];

  DEFAULT_SWARM_MILESTONES.forEach((milestone) => {
    const card =
      cardMap.get(milestone.id) ||
      cardMap.get(`card-${milestone.id}`) ||
      cards.find((c) =>
        c.title.toLowerCase().includes(milestone.title.toLowerCase().slice(0, 8))
      );

    if (card) {
      matchedIds.add(card.id);
      checklist.push({
        id: card.id,
        title: card.title,
        summary: card.summary,
        lane: card.lane,
        status: card.status,
      });
    } else {
      checklist.push(milestone);
    }
  });

  cards.forEach((c) => {
    if (!matchedIds.has(c.id)) {
      checklist.push({
        id: c.id,
        title: c.title,
        summary: c.summary,
        lane: c.lane,
        status: c.status,
      });
    }
  });

  const completedCount = checklist.filter((item) => item.status === "done").length;
  const inProgressCount = checklist.filter(
    (item) => item.status === "in_progress" || item.status === "needs_approval"
  ).length;

  const rawProgress =
    checklist.length > 0
      ? ((completedCount + inProgressCount * 0.4) / checklist.length) * 100
      : 0;

  const progress = Math.min(100, Math.max(0, Math.round(rawProgress)));

  return {
    checklist,
    progress,
    completedCount,
    totalCount: checklist.length,
  };
}

interface BeehiveMascotProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  showText?: boolean;
  progress?: number; // 0 to 100
  checklist?: ChecklistItem[];
  onToggleItem?: (id: string) => void;
  forceOpen?: boolean;
}

export const BeehiveMascot: React.FC<BeehiveMascotProps> = ({
  size = "md",
  className = "",
  showText = false,
  progress = 0,
  checklist = DEFAULT_SWARM_MILESTONES,
  onToggleItem,
  forceOpen = false,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const hoverTimeoutRef = useRef<number | null>(null);
  const rawId = useId();
  const id = rawId.replace(/:/g, "_");

  const showPopover = isHovered || forceOpen;

  const isSm = size === "sm";
  const scale = isSm ? 0.28 : size === "lg" ? 1.3 : 1.0;

  // Clamping progress
  const safeProgress = Math.min(100, Math.max(0, progress));

  // Tiers go from y=10 to y=126 (total 116px height)
  const totalHiveHeight = 116;
  const fillHeight = (totalHiveHeight * safeProgress) / 100;
  const fillY = 126 - fillHeight;

  const completedItems = checklist.filter((i) => i.status === "done");
  const remainingItems = checklist.filter((i) => i.status !== "done");
  const completedCount = completedItems.length;
  const totalCount = checklist.length;

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    hoverTimeoutRef.current = window.setTimeout(() => {
      setIsHovered(false);
    }, 220);
  };

  return (
    <div
      className={`beehive-mascot-container ${size}-size ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div
        className="beehive-stage"
        style={{
          width: isSm ? "42px" : `${240 * scale}px`,
          height: isSm ? "38px" : `${200 * scale}px`,
        }}
      >
        {/* Left Bee */}
        {!isSm && (
          <div
            className={`mascot-bee bee-left ${safeProgress > 0 ? "bee-active" : ""}`}
            style={{
              position: "absolute",
              left: `${15 * scale}px`,
              top: `${100 * scale}px`,
              transform: `scale(${scale})`,
            }}
            title="Worker Bee • Building hive"
          >
            <svg width="34" height="30" viewBox="0 0 34 30" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Wing 1 */}
              <ellipse
                cx="13"
                cy="7"
                rx="6"
                ry="4"
                transform="rotate(-25 13 7)"
                fill="#FFFFFF"
                fillOpacity="0.85"
                stroke="#2E2822"
                strokeWidth="1.2"
                className="bee-wing-flutter"
              />
              {/* Wing 2 */}
              <ellipse
                cx="19"
                cy="6"
                rx="6"
                ry="4"
                transform="rotate(-5 19 6)"
                fill="#FFFFFF"
                fillOpacity="0.7"
                stroke="#2E2822"
                strokeWidth="1.2"
                className="bee-wing-flutter-delayed"
              />
              {/* Body */}
              <ellipse cx="16" cy="18" rx="10" ry="7" fill="#F4A325" stroke="#221E19" strokeWidth="1.6" />
              {/* Stripes */}
              <rect x="12" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
              <rect x="18" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
              {/* Head */}
              <circle cx="25" cy="18" r="4.2" fill="#241F1A" />
              <circle cx="26" cy="17" r="1" fill="#FFFFFF" />
              {/* Antennae */}
              <path d="M26.5 14C27.5 11 29 10 31 10.5" stroke="#241F1A" strokeWidth="1.2" strokeLinecap="round" />
              {/* Stinger */}
              <path d="M6 18L3.5 18" stroke="#241F1A" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </div>
        )}

        {/* Central Beehive */}
        <div
          className={`mascot-hive ${safeProgress === 100 ? "hive-full-pulse" : ""}`}
          style={{
            transform: isSm ? "none" : `scale(${scale})`,
            filter: safeProgress > 0
              ? isSm
                ? "drop-shadow(0 2px 6px rgba(229, 161, 45, 0.4))"
                : "drop-shadow(0 6px 18px rgba(229, 161, 45, 0.35))"
              : isSm
                ? "drop-shadow(0 2px 4px rgba(180, 160, 130, 0.2))"
                : "drop-shadow(0 4px 10px rgba(180, 160, 130, 0.2))",
            cursor: "pointer",
            display: isSm ? "flex" : undefined,
            alignItems: isSm ? "center" : undefined,
            justifyContent: isSm ? "center" : undefined,
          }}
          onClick={() => setIsHovered((prev) => !prev)}
        >
          <svg
            width={isSm ? "42" : "150"}
            height={isSm ? "38" : "136"}
            viewBox="0 0 150 136"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id={`honeyGrad-${id}`} x1="75" y1="10" x2="75" y2="126" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#FFC84B" />
                <stop offset="50%" stopColor="#E5A12D" />
                <stop offset="100%" stopColor="#C57E12" />
              </linearGradient>
              <linearGradient id={`doorGrad-${id}`} x1="75" y1="54" x2="75" y2="88" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#FFD868" />
                <stop offset="100%" stopColor="#E29A1F" />
              </linearGradient>
              <clipPath id={`honeyClip-${id}`}>
                <rect
                  x="0"
                  y={fillY}
                  width="150"
                  height={fillHeight + 20}
                  style={{
                    transition: "y 0.6s cubic-bezier(0.34, 1.25, 0.64, 1), height 0.6s cubic-bezier(0.34, 1.25, 0.64, 1)",
                  }}
                />
              </clipPath>
            </defs>

            {/* BASE EMPTY HIVE (Chambered texture visible when unfilled) */}
            <g className="empty-hive-base">
              {/* Tier 1 */}
              <rect x="52" y="10" width="46" height="16" rx="8" fill="#F7EEDF" stroke="#CBB18B" strokeWidth="1.6" />
              {/* Tier 2 */}
              <rect x="36" y="24" width="78" height="18" rx="9" fill="#F7EEDF" stroke="#CBB18B" strokeWidth="1.6" />
              {/* Tier 3 */}
              <rect x="25" y="40" width="100" height="20" rx="10" fill="#F7EEDF" stroke="#CBB18B" strokeWidth="1.6" />
              {/* Tier 4 */}
              <rect x="18" y="58" width="114" height="22" rx="11" fill="#F7EEDF" stroke="#CBB18B" strokeWidth="1.6" />
              {/* Tier 5 */}
              <rect x="25" y="78" width="100" height="20" rx="10" fill="#F7EEDF" stroke="#CBB18B" strokeWidth="1.6" />
              {/* Tier 6 */}
              <rect x="36" y="96" width="78" height="18" rx="9" fill="#F7EEDF" stroke="#CBB18B" strokeWidth="1.6" />
              {/* Tier 7 */}
              <rect x="52" y="112" width="46" height="14" rx="7" fill="#F7EEDF" stroke="#CBB18B" strokeWidth="1.6" />

              {/* Empty Comb Texture Lines */}
              <path
                d="M60 18 H90 M44 33 H106 M33 50 H117 M26 69 H124 M33 88 H117 M44 105 H106 M60 119 H90"
                stroke="#E2D2B8"
                strokeWidth="1.1"
                strokeDasharray="3 3"
              />

              {/* Empty Doorway */}
              <path
                d="M68 62C68 57.58 71.13 54 75 54C78.87 54 82 57.58 82 62V82C82 85.31 79.31 88 76 88H74C70.69 88 68 85.31 68 82V62Z"
                fill="#ECE0C8"
                stroke="#BA9869"
                strokeWidth="1.2"
              />
              <rect x="71" y="65" width="8" height="20" rx="4" fill="#DEC7A1" />
            </g>

            {/* HONEY FILL LAYER (Revealed by clipPath as progress rises) */}
            <g clipPath={`url(#honeyClip-${id})`} className="honey-fill-group">
              <rect x="52" y="10" width="46" height="16" rx="8" fill={`url(#honeyGrad-${id})`} stroke="#A66103" strokeWidth="1.2" />
              <rect x="36" y="24" width="78" height="18" rx="9" fill={`url(#honeyGrad-${id})`} stroke="#A66103" strokeWidth="1.2" />
              <rect x="25" y="40" width="100" height="20" rx="10" fill={`url(#honeyGrad-${id})`} stroke="#A66103" strokeWidth="1.2" />
              <rect x="18" y="58" width="114" height="22" rx="11" fill={`url(#honeyGrad-${id})`} stroke="#A66103" strokeWidth="1.2" />
              <rect x="25" y="78" width="100" height="20" rx="10" fill={`url(#honeyGrad-${id})`} stroke="#A66103" strokeWidth="1.2" />
              <rect x="36" y="96" width="78" height="18" rx="9" fill={`url(#honeyGrad-${id})`} stroke="#A66103" strokeWidth="1.2" />
              <rect x="52" y="112" width="46" height="14" rx="7" fill={`url(#honeyGrad-${id})`} stroke="#A66103" strokeWidth="1.2" />

              {/* Honey Doorway */}
              <path
                d="M68 62C68 57.58 71.13 54 75 54C78.87 54 82 57.58 82 62V82C82 85.31 79.31 88 76 88H74C70.69 88 68 85.31 68 82V62Z"
                fill={`url(#doorGrad-${id})`}
                stroke="#C47E0C"
                strokeWidth="1.2"
              />
              <rect x="71" y="65" width="8" height="20" rx="4" fill="#995604" />

              {/* Surface meniscus wave at liquid level */}
              {safeProgress > 0 && safeProgress < 100 && (
                <path
                  d={`M 15 ${fillY} Q 45 ${fillY - 3} 75 ${fillY} T 135 ${fillY} L 135 ${fillY + 4} L 15 ${fillY + 4} Z`}
                  fill="#FFF3B8"
                  opacity="0.9"
                />
              )}

              {/* Liquid Sheen */}
              <ellipse cx="60" cy="50" rx="30" ry="12" fill="#FFFFFF" opacity="0.18" transform="rotate(-15 60 50)" />
            </g>

            {/* Dripping honey drops when honey is high */}
            {safeProgress >= 35 && (
              <circle cx="75" cy="89" r="2.5" fill="#E59516" stroke="#995604" strokeWidth="0.8" className="honey-drip-dot" />
            )}
            {safeProgress >= 70 && (
              <path d="M75 126 C73.5 126 72 130 75 133 C78 130 76.5 126 75 126 Z" fill="#E59516" stroke="#995604" strokeWidth="0.8" className="honey-bottom-drip" />
            )}
          </svg>
        </div>

        {/* Right Bee */}
        {!isSm && (
          <div
            className={`mascot-bee bee-right ${safeProgress > 0 ? "bee-active" : ""}`}
            style={{
              position: "absolute",
              right: `${15 * scale}px`,
              top: `${42 * scale}px`,
              transform: `scale(${scale})`,
            }}
            title="QA / Research Bee • Checking nectar"
          >
            <svg width="34" height="30" viewBox="0 0 34 30" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Wing 1 */}
              <ellipse
                cx="19"
                cy="7"
                rx="6"
                ry="4"
                transform="rotate(25 19 7)"
                fill="#FFFFFF"
                fillOpacity="0.85"
                stroke="#2E2822"
                strokeWidth="1.2"
                className="bee-wing-flutter"
              />
              {/* Wing 2 */}
              <ellipse
                cx="13"
                cy="6"
                rx="6"
                ry="4"
                transform="rotate(5 13 6)"
                fill="#FFFFFF"
                fillOpacity="0.7"
                stroke="#2E2822"
                strokeWidth="1.2"
                className="bee-wing-flutter-delayed"
              />
              {/* Body */}
              <ellipse cx="16" cy="18" rx="10" ry="7" fill="#F4A325" stroke="#221E19" strokeWidth="1.6" />
              {/* Stripes */}
              <rect x="13" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
              <rect x="19" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
              {/* Head (facing left) */}
              <circle cx="7" cy="18" r="4.2" fill="#241F1A" />
              <circle cx="6" cy="17" r="1" fill="#FFFFFF" />
              {/* Antennae */}
              <path d="M6 14C5 11 3.5 10 1.5 10.5" stroke="#241F1A" strokeWidth="1.2" strokeLinecap="round" />
              {/* Stinger */}
              <path d="M26 18L28.5 18" stroke="#241F1A" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </div>
        )}
      </div>

      {/* Progress pill badge - only on md and lg sizes */}
      {!isSm && (
        <div
          className="hive-progress-pill-badge"
          onClick={() => setIsHovered((prev) => !prev)}
          title="Click or hover to view task checklist"
        >
          <span className="badge-honey-icon">{safeProgress > 0 ? "🍯" : "🫙"}</span>
          <span className="badge-honey-pct">{safeProgress}% Honey</span>
          <span className="badge-honey-sub">
            {safeProgress === 0
              ? "Empty • Hover for checklist"
              : safeProgress === 100
              ? "Hive Complete! ✨"
              : `${completedCount}/${totalCount} Done • Hover`}
          </span>
        </div>
      )}

      {/* Hover Checklist Popover */}
      {showPopover && (
        <div
          className={`beehive-checklist-popover popover-${size}`}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          role="tooltip"
          aria-label="Swarm progress and remaining checklist"
        >
          {/* Header */}
          <div className="checklist-popover-header">
            <div className="popover-header-left">
              <span className="popover-honey-emoji">🍯</span>
              <div>
                <h4 className="popover-title">HIVE PROGRESS</h4>
                <span className="popover-subtitle">
                  {completedCount} of {totalCount} Milestones Completed
                </span>
              </div>
            </div>
            <div className="popover-pct-badge">
              <span className="pct-num">{safeProgress}%</span>
              <span className="pct-label">HONEY</span>
            </div>
          </div>

          {/* Visual Progress Bar */}
          <div className="checklist-progress-bar-container">
            <div
              className="checklist-progress-bar-fill"
              style={{ width: `${safeProgress}%` }}
            />
          </div>

          {/* Remaining Checklist ("What is left") */}
          <div className="checklist-section what-left-section">
            <div className="checklist-section-title what-left-title">
              <Clock size={12} />
              <span>WHAT'S LEFT TO DO ({remainingItems.length})</span>
            </div>

            {remainingItems.length === 0 ? (
              <div className="checklist-all-done-banner">
                <Sparkles size={15} className="text-amber-600 flex-shrink-0" />
                <span>All swarm milestones reached & verified! Hive is 100% full.</span>
              </div>
            ) : (
              <div className="checklist-items-scroll">
                {remainingItems.map((item) => (
                  <div
                    key={item.id}
                    className="checklist-item remaining-item"
                    onClick={() => onToggleItem?.(item.id)}
                    title={onToggleItem ? "Click to toggle milestone status" : undefined}
                  >
                    <div className="checklist-item-status-icon">
                      {item.status === "in_progress" ? (
                        <Activity size={13} className="text-amber-600 animate-spin-slow" />
                      ) : item.status === "needs_approval" ? (
                        <AlertTriangle size={13} className="text-amber-700 animate-pulse" />
                      ) : (
                        <div className="empty-check-circle" />
                      )}
                    </div>
                    <div className="checklist-item-body">
                      <div className="checklist-item-header">
                        <span className="checklist-item-name">{item.title}</span>
                        {item.lane && (
                          <span className={`checklist-lane-badge lane-${item.lane.toLowerCase()}`}>
                            {item.lane}
                          </span>
                        )}
                      </div>
                      <p className="checklist-item-summary">{item.summary}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Completed Items Section */}
          {completedItems.length > 0 && (
            <div className="checklist-section completed-section">
              <div className="checklist-section-title completed-title">
                <CheckCircle size={12} className="text-emerald-700" />
                <span>COMPLETED ({completedItems.length})</span>
              </div>
              <div className="checklist-items-scroll completed-items-list">
                {completedItems.map((item) => (
                  <div
                    key={item.id}
                    className="checklist-item completed-item"
                    onClick={() => onToggleItem?.(item.id)}
                    title={onToggleItem ? "Click to toggle milestone status" : undefined}
                  >
                    <Check size={12} className="text-emerald-700 flex-shrink-0 mt-0.5" />
                    <div className="checklist-item-body">
                      <span className="checklist-item-name done-strikethrough">{item.title}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer note */}
          <div className="checklist-popover-footer">
            <span>💡 Click 'Run Demo' to watch the swarm complete tasks & fill the hive</span>
          </div>
        </div>
      )}

      {showText && (
        <div style={{ textAlign: "center", marginTop: "10px" }}>
          <h3
            style={{
              fontSize: "16px",
              fontWeight: 700,
              color: "#2E2822",
              letterSpacing: "-0.3px",
              marginBottom: "4px",
            }}
          >
            {safeProgress === 0
              ? "The Hive is Standing By"
              : safeProgress === 100
              ? "The Hive is Complete!"
              : `The Hive is Working (${safeProgress}% Honey)`}
          </h3>
          <p style={{ fontSize: "12px", color: "#7A6C58", maxWidth: "340px", lineHeight: "1.4" }}>
            {safeProgress === 0
              ? "Start the demo scenario to watch the swarm research, build, and verify in real time while filling the hive."
              : safeProgress === 100
              ? "All milestones are done and verified with live evidence. The hive is overflowing with honey!"
              : "Hover over the beehive to view the remaining milestone checklist."}
          </p>
        </div>
      )}
    </div>
  );
};
