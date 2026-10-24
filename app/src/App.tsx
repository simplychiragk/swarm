import { useState } from "react";
import { useSwarmWebSocket } from "./hooks/useSwarmWebSocket";
import { Sidebar } from "./components/Sidebar";
import { HoneycombWhiteboard } from "./components/HoneycombWhiteboard";
import { ApprovalModal } from "./components/ApprovalModal";
import { EvidenceModal } from "./components/EvidenceModal";
import { SettingsModal } from "./components/SettingsModal";
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
    triggerRun,
    resetBoard,
    wsUrl,
  } = useSwarmWebSocket();

  const [selectedEvidence, setSelectedEvidence] = useState<{
    item: EvidenceItem;
    cardTitle: string;
  } | null>(null);

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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

  return (
    <div className="retro-desktop-shell">
      {/* Main Split Layout: Left Sidebar + Right Whiteboard Canvas */}
      <div className="shell-workspace-layout">
        {/* Left Sidebar (Nectar Chat Feed + Project Files Explorer + User Capsule) */}
        <Sidebar
          messages={messages}
          onSendMessage={sendMessage}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />

        {/* Right Whiteboard Canvas (Retro Honeycomb Board with Beehive Mascot & Cards) */}
        <main className="main-canvas-area">
          <HoneycombWhiteboard
            cards={cards}
            status={status}
            onSelectEvidence={(item, cardTitle) => setSelectedEvidence({ item, cardTitle })}
            onRequestApproval={handleRequestApproval}
            onTriggerRun={triggerRun}
            onResetBoard={resetBoard}
          />
        </main>
      </div>

      {/* Contract #3: Approval Modal */}
      <ApprovalModal
        approval={activeApproval}
        onDecision={(decision, note) => sendApprovalDecision(decision, note)}
        onClose={() => setActiveApproval(null)}
      />

      {/* Verified Evidence Inspection Modal */}
      <EvidenceModal
        evidence={selectedEvidence ? selectedEvidence.item : null}
        cardTitle={selectedEvidence?.cardTitle}
        onClose={() => setSelectedEvidence(null)}
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
