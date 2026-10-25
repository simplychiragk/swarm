import { useState, useEffect } from "react";
import { useSwarmWebSocket } from "./hooks/useSwarmWebSocket";
import { Sidebar } from "./components/Sidebar";
import { HoneycombWhiteboard } from "./components/HoneycombWhiteboard";
import { ApprovalModal } from "./components/ApprovalModal";
import { EvidenceModal } from "./components/EvidenceModal";
import { SettingsModal } from "./components/SettingsModal";
import { FileViewerModal, type ProjectFile } from "./components/FileViewerModal";
import type { EvidenceItem, WhiteboardCard } from "./types/contracts";
import "./App.css";

export function App() {
  const {
    status,
    messages,
    cards,
    activeApproval,
    setActiveApproval,
    sendMessage,
    sendApprovalDecision,
    resetBoard,
    wsUrl,
  } = useSwarmWebSocket();

  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [selectedEvidence, setSelectedEvidence] = useState<{
    item: EvidenceItem;
    cardTitle: string;
  } | null>(null);

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [viewingFile, setViewingFile] = useState<ProjectFile | null>(null);

  // Keyboard shortcut Ctrl+B or Cmd+B to toggle sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setIsSidebarOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleRequestApproval = (card: WhiteboardCard) => {
    // If a card with needs_approval is clicked, open/restore approval prompt
    setActiveApproval({
      id: `appr-manual-${card.id}`,
      card_id: card.id,
      prompt: `Card '${card.title}' is flagged for human sign-off. Do you authorize this step?`,
      options: ["Approve", "Redirect"],
      lane: card.lane,
      card,
      created_at: new Date().toISOString(),
    });
  };

  const handleSaveContent = async (path: string, newContent: string) => {
    try {
      const cleanPath = path.replace(/^frontend\//, "").replace(/^project\//, "");
      const res = await fetch(`http://127.0.0.1:8000/workspace/files/${cleanPath}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newContent }),
      });
      if (res.ok) {
        setViewingFile((prev) => (prev ? { ...prev, content: newContent } : null));
      }
    } catch (e) {
      console.error("Failed to save file to workspace:", e);
    }
  };

  return (
    <div className="retro-desktop-shell">
      {/* Main Split Layout: Left Sidebar + Right Whiteboard Canvas */}
      <div className={`shell-workspace-layout ${!isSidebarOpen ? "sidebar-is-collapsed" : ""}`}>
        {/* Left Sidebar (Nectar Chat Feed + Project Files Explorer + User Capsule) */}
        <Sidebar
          messages={messages}
          onSendMessage={sendMessage}
          onResetBoard={resetBoard}
          onOpenSettings={() => setIsSettingsOpen(true)}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          onOpenFile={(file) => setViewingFile(file)}
        />

        {/* Right Whiteboard Canvas (Retro Honeycomb Board with Beehive Mascot & Cards) */}
        <main className="main-canvas-area">
          <HoneycombWhiteboard
            cards={cards}
            status={status}
            onSelectEvidence={(item, cardTitle) => setSelectedEvidence({ item, cardTitle })}
            onRequestApproval={handleRequestApproval}
            onResetBoard={resetBoard}
            isSidebarOpen={isSidebarOpen}
            onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          />
        </main>
      </div>

      {/* Contract #3: Approval Modal */}
      <ApprovalModal
        approval={activeApproval}
        cards={cards}
        onDecision={(decision, note, scope) => sendApprovalDecision(decision, note, scope)}
        onClose={() => setActiveApproval(null)}
      />

      {/* Verified Evidence Inspection Modal */}
      <EvidenceModal
        evidence={selectedEvidence ? selectedEvidence.item : null}
        cardTitle={selectedEvidence?.cardTitle}
        onClose={() => setSelectedEvidence(null)}
      />

      {/* Interactive Project File Code Preview Modal */}
      <FileViewerModal
        file={viewingFile}
        onClose={() => setViewingFile(null)}
        onSaveContent={handleSaveContent}
      />

      {/* System Settings & Runtime Config */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        status={status}
        wsUrl={wsUrl}
      />
    </div>
  );
}

export default App;
