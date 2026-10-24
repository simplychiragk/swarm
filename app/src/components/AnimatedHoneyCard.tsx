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

  // Stagger delay based on card index (e.g. 0s, 0.18s, 0.36s)
  const staggerDelay = Math.min(index * 0.18, 0.9);
  const cardAppearDelay = staggerDelay + 0.45;
  const contentFadeDelay = staggerDelay + 0.7;

  // Cleanup flight overlay after animation completes (~1.7s) to free resources
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimationFinished(true);
    }, (staggerDelay + 1.8) * 1000);
    return () => clearTimeout(timer);
  }, [staggerDelay]);

  // Whimsical looping bee flight path that circles around and behind the card perimeter
  const flightPathD =
    "M 370 -15 " +
    "C 350 15, 310 25, 330 65 " +
    "C 352 105, 375 55, 350 15 " +
    "C 335 40, 345 110, 355 170 " +
    "C 365 215, 320 238, 260 234 " +
    "C 200 230, 160 250, 140 235 " +
    "C 120 218, 142 202, 165 212 " +
    "C 185 224, 120 235, 70 230 " +
    "C 15 225, -12 180, 5 120 " +
    "C 18 55, -8 18, 25 -5 " +
    "C 65 -30, 145 -15, 225 -22 " +
    "C 295 -28, 338 -5, 332 25";

  return (
    <div className="animated-card-stage">
      {/* SVG Bee & Dotted Trail Animation Overlay */}
      {!animationFinished && (
        <svg
          className="bee-flight-svg-overlay"
          viewBox="-35 -35 425 295"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            {/* Subtle glow for the dotted bee trail */}
            <filter id={`trail-glow-${card.id}`} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="1" floodColor="#C57E12" floodOpacity="0.3" />
            </filter>
          </defs>

          {/* Dotted Bee Trail that draws in behind the flying bee */}
          <path
            d={flightPathD}
            className="bee-dotted-trail"
            style={{
              animationDelay: `${staggerDelay}s`,
            }}
            filter={`url(#trail-glow-${card.id})`}
          />

          {/* Sparkle puff where the bee arrives and takes off */}
          <g
            className="bee-trail-sparkle"
            style={{
              animationDelay: `${contentFadeDelay}s`,
            }}
            transform="translate(332, 25)"
          >
            <circle cx="0" cy="0" r="3" fill="#F4A325" opacity="0.9" />
            <path d="M-6 0 L6 0 M0 -6 L0 6" stroke="#E59E27" strokeWidth="1.2" />
          </g>

          {/* The Flying Worker Bee that roams around the card */}
          <g className="flying-worker-bee-container">
            <animateMotion
              path={flightPathD}
              dur="1.45s"
              rotate="auto"
              fill="freeze"
              begin={`${staggerDelay}s`}
            />

            {/* Render Bee Graphic */}
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

              {/* Antennae */}
              <path d="M26.5 14C27.5 11 29 10 31 10.5" stroke="#241F1A" strokeWidth="1.2" strokeLinecap="round" />
              {/* Stinger */}
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
