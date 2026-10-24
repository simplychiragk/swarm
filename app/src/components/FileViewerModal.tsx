import React, { useState } from "react";
import { X, Copy, Check, FileCode, Save } from "lucide-react";

export interface ProjectFile {
  name: string;
  path: string;
  language: string;
  content: string;
}

interface FileViewerModalProps {
  file: ProjectFile | null;
  onClose: () => void;
  onSaveContent?: (path: string, newContent: string) => void;
}

export const FileViewerModal: React.FC<FileViewerModalProps> = ({
  file,
  onClose,
  onSaveContent,
}) => {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState("");
  const [savedToast, setSavedToast] = useState(false);

  // Initialize edited content when file opens
  React.useEffect(() => {
    if (file) {
      setEditedContent(file.content);
      setIsEditing(false);
      setCopied(false);
    }
  }, [file]);

  if (!file) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(isEditing ? editedContent : file.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSave = () => {
    if (onSaveContent) {
      onSaveContent(file.path, editedContent);
    }
    setIsEditing(false);
    setSavedToast(true);
    setTimeout(() => setSavedToast(false), 2000);
  };

  const lines = (isEditing ? editedContent : file.content).split("\n");

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="file-viewer-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="file-viewer-title"
      >
        {/* Modal Header */}
        <div className="file-viewer-header">
          <div className="file-header-left">
            <span className="file-header-icon">
              <FileCode size={18} />
            </span>
            <div>
              <h3 id="file-viewer-title" className="file-header-title">
                {file.name}
              </h3>
              <p className="file-header-path">{file.path}</p>
            </div>
          </div>

          <div className="file-header-actions">
            <span className="file-meta-tag">{file.language.toUpperCase()}</span>
            <span className="file-meta-lines">{lines.length} lines</span>

            <button
              type="button"
              className="retro-icon-action-btn"
              onClick={handleCopy}
              title="Copy code to clipboard"
            >
              {copied ? <Check size={14} className="text-emerald-700" /> : <Copy size={14} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>

            {isEditing ? (
              <button
                type="button"
                className="retro-icon-action-btn save-active-btn"
                onClick={handleSave}
                title="Save file changes"
              >
                <Save size={14} />
                <span>Save</span>
              </button>
            ) : (
              <button
                type="button"
                className="retro-icon-action-btn"
                onClick={() => setIsEditing(true)}
                title="Edit file content"
              >
                <span>Edit</span>
              </button>
            )}

            <button
              type="button"
              className="retro-icon-btn"
              onClick={onClose}
              aria-label="Close file viewer"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {savedToast && (
          <div className="file-saved-banner">
            ✓ Changes saved successfully to {file.name}
          </div>
        )}

        {/* Modal Code Body with Line Numbers */}
        <div className="file-viewer-body">
          {isEditing ? (
            <textarea
              className="file-editor-textarea"
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              spellCheck={false}
              autoFocus
            />
          ) : (
            <div className="code-viewer-container">
              <div className="line-numbers-column" aria-hidden="true">
                {lines.map((_, idx) => (
                  <span key={idx} className="line-number">
                    {idx + 1}
                  </span>
                ))}
              </div>
              <pre className="code-content-column">
                <code>{file.content}</code>
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="file-viewer-footer">
          <span className="editor-status-hint">
            {isEditing ? "Editing Mode • Press Save when done" : "Viewing file • Read-only preview"}
          </span>
          <button type="button" className="retro-btn retro-btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
