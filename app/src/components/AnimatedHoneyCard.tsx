import React, { useState, useEffect } from "react";
import type { WhiteboardCard, EvidenceItem, CardStatus } from "../types/contracts";
import { Sparkles, ExternalLink, ShieldCheck } from "lucide-react";

interface AnimatedHoneyCardProps {
  card: WhiteboardCard;
  index: number;
  onSelectEvidence: (evidence: EvidenceItem, cardTitle: string) => void;
  onRequestApproval: (card: WhiteboardCard) => void;
  getStatusIcon: (status: CardStatus) => React.ReactNode;
  getStatusLabel: (status: CardStatus) => string;
}

export const AnimatedHoneyCard: React.FC<AnimatedHoneyCardProps> = ({
  card,
  index,
  onSelectEvidence,
  onRequestApproval,
  getStatusIcon,
  getStatusLabel,
}) => {
  const [animationFinished, setAnimationFinished] = useState(false);
  const isNeedsApproval = card.status === "needs_approval";

  // Relaxed, gentle pacing: stagger by index
  const staggerDelay = Math.min(index * 0.22, 0.88);
  const cardAppearDelay = staggerDelay + 1.2;
  const contentFadeDelay = staggerDelay + 1.7;

  // Cleanup flight overlay after flight & fade finishes (~3.5s)
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimationFinished(true);
    }, (staggerDelay + 3.6) * 1000);
    return () => clearTimeout(timer);
  }, [staggerDelay]);

  // Clean, tight, perimeter path right around the card's rounded border (reduced distance)
  // Hugs ~10px outside the card's 340x220 bounds with smooth rounded corners
  const flightPathD =
    "M 260 -8 " +
    "C 295 -8, 344 6, 344 35 " +
    "L 344 185 " +
    "C 344 214, 305 226, 270 226 " +
    "L 70 226 " +
    "C 35 226, -4 214, -4 185 " +
    "L -4 35 " +
    "C -4 6, 35 -8, 70 -8 " +
    "L 270 -8 " +
    "C 290 -8, 308 -14, 304 -2 " +
    "C 300 8, 285 2, 295 0";

  return (
    <div className="animated-card-stage">
      {/* SVG Bee & Dotted Trail Animation Overlay */}
      {!animationFinished && (
        <svg
          className="bee-flight-svg-overlay"
          viewBox="-25 -25 390 270"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            {/* Dynamic trail mask that reveals dots ONLY behind the bee and fades them out behind */}
            <mask id={`trail-mask-${card.id}`}>
              <path
                d={flightPathD}
                fill="none"
                stroke="white"
                strokeWidth="18"
                strokeLinecap="round"
                className="trail-mask-path"
                style={{
                  animationDelay: `${staggerDelay}s`,
                }}
              />
            </mask>

            {/* Subtle warm glow for the dotted bee trail */}
            <filter id={`trail-glow-${card.id}`} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="1.2" floodColor="#C57E12" floodOpacity="0.35" />
            </filter>
          </defs>

          {/* Dotted Bee Trail that ONLY shows as the bee flies and fades behind it */}
          <path
            d={flightPathD}
            className="bee-dotted-trail"
            mask={`url(#trail-mask-${card.id})`}
            filter={`url(#trail-glow-${card.id})`}
          />

          {/* Gentle finish sparkle near card corner */}
          <g
            className="bee-trail-sparkle"
            style={{
              animationDelay: `${staggerDelay + 2.7}s`,
            }}
            transform="translate(295, 0)"
          >
            <circle cx="0" cy="0" r="2.5" fill="#F4A325" opacity="0.9" />
            <path d="M-5 0 L5 0 M0 -5 L0 5" stroke="#E59E27" strokeWidth="1" />
          </g>

          {/* The Flying Worker Bee that roams around the card at a relaxed, gentle pace */}
          <g
            className="flying-worker-bee-container"
            style={{
              animationDelay: `${staggerDelay}s`,
            }}
          >
            <animateMotion
              path={flightPathD}
              dur="3.0s"
              rotate="auto"
              fill="freeze"
              begin={`${staggerDelay}s`}
            />

            {/* Bee Graphic */}
            <g transform="translate(-16, -14) scale(0.72)">
              {/* Fluttering Wings */}
              <ellipse
                cx="13"
                cy="7"
                rx="6"
                ry="4"
                transform="rotate(-25 13 7)"
                fill="#FFFFFF"
                fillOpacity="0.88"
                stroke="#2E2822"
                strokeWidth="1.2"
                className="bee-wing-flutter"
              />
              <ellipse
                cx="19"
                cy="6"
                rx="6"
                ry="4"
                transform="rotate(-5 19 6)"
                fill="#FFFFFF"
                fillOpacity="0.75"
                stroke="#2E2822"
                strokeWidth="1.2"
                className="bee-wing-flutter-delayed"
              />

              {/* Striped Bee Body */}
              <ellipse cx="16" cy="18" rx="10" ry="7" fill="#F4A325" stroke="#221E19" strokeWidth="1.6" />
              <rect x="12" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
              <rect x="18" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />

              {/* Head with Eye */}
              <circle cx="25" cy="18" r="4.2" fill="#241F1A" />
              <circle cx="26" cy="17" r="1.1" fill="#FFFFFF" />

              {/* Antennae & Stinger */}
              <path d="M26.5 14C27.5 11 29 10 31 10.5" stroke="#241F1A" strokeWidth="1.2" strokeLinecap="round" />
              <path d="M6 18L3.5 18" stroke="#241F1A" strokeWidth="1.6" strokeLinecap="round" />
            </g>
          </g>
        </svg>
      )}

      {/* The Actual Honeycomb Card with smooth staggered emergence */}
      <article
        className={`honey-card honey-card-entrance honey-status-${card.status} ${
          isNeedsApproval ? "card-pulse-approval" : ""
        }`}
        style={{
          animationDelay: `${cardAppearDelay}s`,
        }}
      >
        {/* Card Content that gracefully fades in following the bee's flight */}
        <div
          className="honey-card-content-fade"
          style={{
            animationDelay: `${contentFadeDelay}s`,
          }}
        >
          {/* Card Top Header */}
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
        </div>
      </article>
    </div>
  );
};
