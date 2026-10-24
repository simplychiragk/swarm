import React, { useState, useEffect } from "react";
import type { ApprovalRequest } from "../types/contracts";
import { ShieldCheck, AlertCircle, ArrowRight, CornerDownLeft, Sparkles, X, Loader2, Lock, Terminal } from "lucide-react";

interface ApprovalModalProps {
  approval: ApprovalRequest | null;
  onDecision: (decision: "approve" | "redirect", note?: string, scope?: "once" | "run") => void;
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
  const [scope, setScope] = useState<"once" | "run">("once");

  useEffect(() => {
    setIsSubmitting(false);
    setShowNoteField(false);
    setRedirectNote("");
    setScope("once");
  }, [approval?.id]);

  if (!approval) return null;

  const handleApprove = () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    onDecision("approve", "Approved by user", scope);
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

  const hasSecurityDetails = Boolean(
    approval.tool || approval.risk || approval.reason || approval.args_preview
  );

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
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {approval.risk && (
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  background: approval.risk.toLowerCase() === "high" ? "#fee2e2" : "#fef3c7",
                  color: approval.risk.toLowerCase() === "high" ? "#991b1b" : "#92400e",
                  border: `1px solid ${approval.risk.toLowerCase() === "high" ? "#f87171" : "#fcd34d"}`,
                }}
              >
                {approval.risk} RISK
              </span>
            )}
            <span className="lane-badge-chip">
              Lane: {approval.lane}
            </span>
            {onClose && (
              <button
                type="button"
                className="retro-icon-btn"
                onClick={onClose}
                aria-label="Close approval dialog"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Content Body */}
        <div className="approval-modal-body">
          <div className="approval-prompt-box">
            <AlertCircle size={20} className="prompt-icon" />
            <p className="approval-prompt-text">{approval.prompt}</p>
          </div>

          {/* Security Guard Context */}
          {hasSecurityDetails && (
            <div className="approval-card-preview" style={{ marginTop: "12px", borderLeft: "3px solid #e5a12d" }}>
              <div className="card-preview-header">
                <span className="card-preview-label" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Lock size={12} /> Security Policy Enforcer
                </span>
                {approval.agent && (
                  <span className="card-preview-status">Agent: {approval.agent}</span>
                )}
              </div>
              {approval.tool && (
                <div style={{ fontSize: "13px", margin: "4px 0", color: "#27272a" }}>
                  <strong>Tool Requested:</strong> <code style={{ background: "#f4f4f5", padding: "1px 5px", borderRadius: "3px" }}>{approval.tool}</code>
                </div>
              )}
              {approval.reason && (
                <p className="card-preview-summary" style={{ margin: "4px 0" }}>
                  {approval.reason}
                </p>
              )}
              {approval.args_preview && (
                <div style={{ marginTop: "6px" }}>
                  <span className="evidence-header" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Terminal size={11} /> Redacted Arguments:
                  </span>
                  <pre
                    style={{
                      fontSize: "11px",
                      background: "#18181b",
                      color: "#a1a1aa",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      maxHeight: "100px",
                      overflow: "auto",
                      marginTop: "4px",
                    }}
                  >
                    {typeof approval.args_preview === "string"
                      ? approval.args_preview
                      : JSON.stringify(approval.args_preview, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

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

          {/* Scope Selector if run-level option is available */}
          {approval.scope_options && approval.scope_options.includes("run") && approval.risk?.toLowerCase() !== "high" && (
            <div style={{ marginTop: "12px", display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", color: "#3f3f46" }}>
                <input
                  type="checkbox"
                  checked={scope === "run"}
                  onChange={(e) => setScope(e.target.checked ? "run" : "once")}
                />
                Remember approval for identical actions for the rest of this run
              </label>
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
            <span>
              {isSubmitting
                ? "Authorizing..."
                : scope === "run"
                ? "Approve for Entire Run"
                : "Approve Action"}
            </span>
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
