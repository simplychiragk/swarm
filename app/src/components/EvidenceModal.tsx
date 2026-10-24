import React from "react";
import type { EvidenceItem } from "../types/contracts";
import { X, ExternalLink, FileSearch, CheckCircle2, Camera } from "lucide-react";

interface EvidenceModalProps {
  evidence: EvidenceItem | null;
  cardTitle?: string;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({
  evidence,
  cardTitle,
  onClose,
}) => {
  if (!evidence) return null;

  const isScreenshot =
    evidence.kind === "screenshot" ||
    evidence.url_or_text.endsWith(".png") ||
    evidence.url_or_text.endsWith(".jpg") ||
    evidence.url_or_text.includes("image");

  const isUrl = evidence.url_or_text.startsWith("http");

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="evidence-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-title"
      >
        <div className="evidence-modal-header">
          <div className="evidence-title-group">
            {isScreenshot ? (
              <Camera size={18} className="evidence-icon" />
            ) : (
              <FileSearch size={18} className="evidence-icon" />
            )}
            <div>
              <h3 id="evidence-title" className="evidence-title">
                Verified Verification Evidence
              </h3>
              {cardTitle && <p className="evidence-card-subtitle">{cardTitle}</p>}
            </div>
          </div>
          <button
            type="button"
            className="retro-icon-btn"
            onClick={onClose}
            aria-label="Close evidence preview"
          >
            <X size={16} />
          </button>
        </div>

        <div className="evidence-modal-body">
          <div className="evidence-meta-pill">
            <span className="meta-kind-tag">Evidence Type: {evidence.kind}</span>
            <span className="meta-verified-tag">
              <CheckCircle2 size={12} /> TinyFish Verified
            </span>
          </div>

          {isScreenshot ? (
            <div className="screenshot-preview-box">
              <div className="screenshot-mock-browser">
                <div className="browser-dots">
                  <span className="dot red" />
                  <span className="dot yellow" />
                  <span className="dot green" />
                </div>
                <span className="browser-url-bar">http://localhost:5173/waitlist</span>
              </div>
              <div className="screenshot-inner-viewport">
                <div className="mock-waitlist-preview">
                  <div className="mock-badge">🐝 SWARM LAUNCH</div>
                  <h2 className="mock-heading">Join the Swarm Waitlist</h2>
                  <p className="mock-desc">The multi-agent AI coding swarm that builds with you, in the open.</p>
                  <div className="mock-form-box">
                    <div className="mock-input">developer@example.com</div>
                    <button className="mock-submit">Join Priority Access</button>
                  </div>
                  <div className="mock-toast-success">
                    ✓ You are #42 on the waitlist! Confirmation sent.
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="evidence-text-content">
              <pre className="evidence-pre">{evidence.url_or_text}</pre>
            </div>
          )}

          {isUrl && (
            <div className="evidence-link-row">
              <a
                href={evidence.url_or_text}
                target="_blank"
                rel="noreferrer"
                className="evidence-url-link"
              >
                <span>Open external resource link</span>
                <ExternalLink size={14} />
              </a>
            </div>
          )}
        </div>

        <div className="evidence-modal-footer">
          <button type="button" className="retro-btn retro-btn-secondary" onClick={onClose}>
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
};
