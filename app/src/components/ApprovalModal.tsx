import React, { useState, useEffect } from "react";
import type { ApprovalRequest } from "../types/contracts";
import { ShieldCheck, AlertCircle, ArrowRight, CornerDownLeft, Sparkles, Loader2 } from "lucide-react";

interface ApprovalModalProps {
  approval: ApprovalRequest | null;
  onDecision: (decision: "approve" | "redirect", note?: string) => void;
  onClose?: () => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  approval,
  onDecision,
  onClose,
}) => {
  const [redirectNote, setRedirectNote] = useState("");
  const [showNoteField, setShowNoteField] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setIsSubmitting(false);
    setShowNoteField(false);
    setRedirectNote("");
  }, [approval?.id]);

  if (!approval) return null;

  const handleApprove = () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    onDecision("approve", "Approved by user");
  };

  const handleRedirect = () => {
    if (!showNoteField) {
      setShowNoteField(true);
      return;
    }
    if (isSubmitting) return;
    setIsSubmitting(true);
    onDecision("redirect", redirectNote.trim() || "Revision requested by user");
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="approval-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="approval-title"
      >
        {/* Header Ribbon */}
        <div className="approval-modal-header">
          <div className="approval-badge-group">
            <span className="approval-shield-icon">
              <ShieldCheck size={18} />
            </span>
            <div>
              <h2 id="approval-title" className="approval-header-title">
                Decision Layer Authorization
              </h2>
              <span className="approval-header-sub">
                Rule-Based Gate • Swarm Human-in-the-Loop
              </span>
            </div>
          </div>
          <span className="lane-badge-chip">
            Lane: {approval.lane}
          </span>
        </div>

        {/* Content Body */}
        <div className="approval-modal-body">
          <div className="approval-prompt-box">
            <AlertCircle size={20} className="prompt-icon" />
            <p className="approval-prompt-text">{approval.prompt}</p>
          </div>

          {/* Associated Card Details */}
          {approval.card && (
            <div className="approval-card-preview">
              <div className="card-preview-header">
                <span className="card-preview-label">Target Milestone Card</span>
                <span className="card-preview-status">{approval.card.status.replace("_", " ")}</span>
              </div>
              <h4 className="card-preview-title">{approval.card.title}</h4>
              <p className="card-preview-summary">{approval.card.summary}</p>

              {approval.card.evidence && approval.card.evidence.length > 0 && (
                <div className="card-preview-evidence">
                  <span className="evidence-header">Verified Attachments:</span>
                  <div className="evidence-chips">
                    {approval.card.evidence.map((item, idx) => (
                      <span key={idx} className="evidence-chip">
                        <Sparkles size={11} /> {item.kind}: {item.url_or_text}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Note input if redirecting */}
          {showNoteField && (
            <div className="redirect-note-box">
              <label htmlFor="revision-note" className="note-label">
                Revision feedback or instructions for the swarm:
              </label>
              <textarea
                id="revision-note"
                className="note-textarea"
                rows={3}
                placeholder="e.g. Adjust the waitlist button color to amber; add email format validation..."
                value={redirectNote}
                onChange={(e) => setRedirectNote(e.target.value)}
                autoFocus
              />
            </div>
          )}
        </div>

        {/* Actions Footer */}
        <div className="approval-modal-footer">
          <button
            type="button"
            className="retro-btn retro-btn-approve"
            onClick={handleApprove}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <ShieldCheck size={16} />
            )}
            <span>{isSubmitting ? "Deploying Live..." : "Approve & Deploy Live"}</span>
          </button>

          <button
            type="button"
            className="retro-btn retro-btn-redirect"
            onClick={handleRedirect}
            disabled={isSubmitting}
          >
            {showNoteField ? (
              <>
                <CornerDownLeft size={16} />
                <span>Submit Revision</span>
              </>
            ) : (
              <>
                <ArrowRight size={16} />
                <span>Request Revision</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
