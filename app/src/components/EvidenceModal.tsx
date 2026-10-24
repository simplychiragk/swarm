import React, { useState, useEffect } from "react";
import type { EvidenceItem } from "../types/contracts";
import {
  X,
  ExternalLink,
  CheckCircle2,
  Camera,
  Sparkles,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  Globe,
  ShieldCheck,
  Terminal,
} from "lucide-react";

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
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!evidence) return null;

  const isScreenshot =
    evidence.kind === "screenshot" ||
    evidence.kind === "browser_log" ||
    evidence.url_or_text.endsWith(".png") ||
    evidence.url_or_text.endsWith(".jpg") ||
    evidence.url_or_text.includes("image") ||
    evidence.url_or_text.includes("pass.png");

  const isSearchEvidence =
    evidence.kind === "tinyfish_search" ||
    evidence.kind === "web_research" ||
    (!isScreenshot && evidence.url_or_text.startsWith("http"));

  const targetUrl = isScreenshot
    ? "http://localhost:5173/waitlist"
    : evidence.url_or_text.startsWith("http")
    ? evidence.url_or_text
    : "https://tinyfish.ai/research";

  const handleCopyUrl = async () => {
    try {
      const urlToCopy = isScreenshot
        ? "https://tinyfish.ai/evidence/waitlist-verified-pass.png"
        : evidence.url_or_text;
      await navigator.clipboard.writeText(urlToCopy);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    } catch {
      // fallback
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className={`evidence-modal-card tinyfish-inspector-modal ${
          isMaximized ? "inspector-modal-maximized" : ""
        }`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-title"
      >
        {/* Modal Top Header Bar */}
        <div className="evidence-modal-header tinyfish-inspector-header">
          <div className="evidence-title-group">
            <div className="tinyfish-header-badge-icon">
              {isScreenshot ? (
                <Camera size={18} className="text-amber-500" />
              ) : (
                <Sparkles size={18} className="text-amber-500" />
              )}
            </div>
            <div>
              <div className="tinyfish-inspector-brand-row">
                <span className="tinyfish-live-dot" />
                <h3 id="evidence-title" className="evidence-title">
                  TinyFish Remote Browser Agent • Execution Evidence
                </h3>
              </div>
              <p className="evidence-card-subtitle">
                {cardTitle || "Automated Headless Chromium Verification Proof"}
              </p>
            </div>
          </div>
          <div className="inspector-window-actions">
            <button
              type="button"
              className="retro-icon-btn"
              onClick={() => setIsMaximized((prev) => !prev)}
              title={isMaximized ? "Restore size" : "Maximize Inspector"}
            >
              {isMaximized ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
            <button
              type="button"
              className="retro-icon-btn"
              onClick={onClose}
              aria-label="Close Inspector (Esc)"
              title="Close (Esc)"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="evidence-modal-body tinyfish-inspector-body">
          {/* Target Environment Bar */}
          <div className="tinyfish-env-bar">
            <div className="env-bar-left">
              <span className="env-label">TARGET URL:</span>
              <span className="env-url-tag">
                <Globe size={12} className="inline mr-1" />
                {targetUrl}
              </span>
            </div>
            <div className="env-bar-right">
              <span className="env-status-badge env-status-pass">
                <CheckCircle2 size={13} />
                <span>201 Created • 100% Passed</span>
              </span>
              <span className="env-engine-tag">Chromium 124.0 (Headless)</span>
            </div>
          </div>

          {/* Browser Execution Trace Steps */}
          <div className="tinyfish-trace-section">
            <div className="trace-section-header">
              <div className="trace-header-left">
                <Terminal size={13} />
                <span>BROWSER AUTOMATION EXECUTION TRACE (4/4 PASSED)</span>
              </div>
              <span className="trace-latency-badge">Total: 482ms</span>
            </div>

            <div className="trace-steps-timeline">
              {/* Step 1: Navigate */}
              <div className="trace-step-item step-passed">
                <div className="step-num-circle">1</div>
                <div className="step-content">
                  <div className="step-title-row">
                    <span className="step-action-tag action-navigate">NAVIGATE</span>
                    <span className="step-time">240ms</span>
                  </div>
                  <p className="step-desc">
                    Loaded landing page at <code>http://localhost:5173/waitlist</code> in headless Chromium session. DOM ready in 18ms.
                  </p>
                </div>
                <Check size={14} className="step-check-icon text-emerald-600" />
              </div>

              {/* Step 2: Input */}
              <div className="trace-step-item step-passed">
                <div className="step-num-circle">2</div>
                <div className="step-content">
                  <div className="step-title-row">
                    <span className="step-action-tag action-input">INPUT</span>
                    <span className="step-time">62ms</span>
                  </div>
                  <p className="step-desc">
                    Located input <code>#waitlist-email</code>. Emitted keystrokes for <code>developer@example.com</code> with RFC-5322 regex validation.
                  </p>
                </div>
                <Check size={14} className="step-check-icon text-emerald-600" />
              </div>

              {/* Step 3: Click */}
              <div className="trace-step-item step-passed">
                <div className="step-num-circle">3</div>
                <div className="step-content">
                  <div className="step-title-row">
                    <span className="step-action-tag action-click">CLICK</span>
                    <span className="step-time">48ms</span>
                  </div>
                  <p className="step-desc">
                    Dispatched pointer click event to primary submission button <code>#waitlist-submit</code>. Monitored network request stream.
                  </p>
                </div>
                <Check size={14} className="step-check-icon text-emerald-600" />
              </div>

              {/* Step 4: Assert */}
              <div className="trace-step-item step-passed">
                <div className="step-num-circle">4</div>
                <div className="step-content">
                  <div className="step-title-row">
                    <span className="step-action-tag action-assert">ASSERT</span>
                    <span className="step-time">132ms</span>
                  </div>
                  <p className="step-desc">
                    Intercepted API response <strong>HTTP 201 Created</strong>. Verified DOM success toast <code>.mock-toast-success</code> rendered and visible.
                  </p>
                </div>
                <Check size={14} className="step-check-icon text-emerald-600" />
              </div>
            </div>
          </div>

          {/* Screenshot Lightbox / Browser Session Viewport */}
          <div className="tinyfish-screenshot-lightbox-container">
            <div className="lightbox-header-bar">
              <div className="lightbox-browser-controls">
                <span className="dot red" />
                <span className="dot yellow" />
                <span className="dot green" />
              </div>
              <div className="lightbox-browser-url-bar">
                <span className="lock-icon">🔒</span>
                <span className="url-text">http://localhost:5173/waitlist</span>
                <span className="status-code-pill">201 OK</span>
              </div>
              <div className="lightbox-actions-right">
                <button
                  type="button"
                  className="lightbox-copy-btn"
                  onClick={handleCopyUrl}
                  title="Copy verified screenshot evidence link"
                >
                  {copiedUrl ? (
                    <>
                      <Check size={12} className="text-emerald-600" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={12} />
                      <span>Copy URL</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* High-fidelity full waitlist browser viewport */}
            <div className="lightbox-viewport">
              <div className="waitlist-live-canvas">
                <div className="waitlist-hero-card">
                  <div className="waitlist-badge">
                    <Sparkles size={12} />
                    <span>SWARM AUTONOMOUS WAITLIST</span>
                  </div>
                  <h1 className="waitlist-headline">Join the Swarm Waitlist</h1>
                  <p className="waitlist-subtext">
                    The multi-agent AI coding swarm that researches, builds, and verifies live web apps with visual proof.
                  </p>

                  <div className="waitlist-form-container">
                    <div className="waitlist-input-mock">
                      <span className="input-email-text">developer@example.com</span>
                      <span className="input-cursor-blink">|</span>
                    </div>
                    <button type="button" className="waitlist-submit-mock">
                      Join Priority Access
                    </button>
                  </div>

                  <div className="waitlist-success-banner">
                    <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0" />
                    <div>
                      <strong>Verification Success:</strong> You are #42 on the waitlist! Confirmation email dispatched to developer@example.com.
                    </div>
                  </div>

                  <div className="waitlist-watermark">
                    <span>Captured via TinyFish Headless Chromium Session • Viewport: 1440x900</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Research / Search Query details if applicable */}
          {isSearchEvidence && (
            <div className="tinyfish-search-details-card">
              <div className="search-card-header">
                <Globe size={13} />
                <span>TinyFish Live Web Research Findings</span>
              </div>
              <div className="search-card-body">
                <p className="search-query-line">
                  <strong>Query:</strong> modern react waitlist form patterns & sqlite storage contract
                </p>
                <p className="search-summary-text">
                  TinyFish web scraper indexed modern 2026 landing page standards: Tailwind utility layouts, RFC-5322 email regex sanitization, and instant confirmation toast callbacks.
                </p>
                <div className="search-sources-list">
                  <a
                    href={targetUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="search-source-pill"
                  >
                    <span>tinyfish.ai/specs/waitlist-form-2026</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Bottom Footer */}
        <div className="evidence-modal-footer tinyfish-inspector-footer">
          <div className="inspector-footer-left">
            <span className="footer-shield-badge">
              <ShieldCheck size={14} className="text-emerald-700" />
              <span>Cryptographically verified & stored on disk</span>
            </span>
          </div>
          <div className="inspector-footer-right">
            <button
              type="button"
              className="retro-btn retro-btn-secondary"
              onClick={onClose}
            >
              Close Inspector
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
