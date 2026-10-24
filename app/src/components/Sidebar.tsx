import React, { useState, useRef, useEffect } from "react";
import type { FeedMessage, AgentSender } from "../types/contracts";
import {
  Settings,
  PanelLeftClose,
  Folder,
  ChevronDown,
  ChevronRight,
  FileCheck,
  Search,
  Send,
  MessageSquare,
  Sparkles,
  Bot,
  User,
  FlaskConical,
  Scroll,
  Crown,
  Plus,
  RefreshCw,
  FolderPlus,
} from "lucide-react";

interface SidebarProps {
  messages: FeedMessage[];
  onSendMessage: (text: string) => void;
  onOpenSettings: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  messages,
  onSendMessage,
  onOpenSettings,
  isSidebarOpen,
  onToggleSidebar,
}) => {
  const [activeTab, setActiveTab] = useState<"feed" | "files">("feed");
  const [inputText, setInputText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchInput, setShowSearchInput] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    project: true,
    frontend: false,
    src: true,
  });

  const feedBottomRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll feed to bottom when new messages arrive
  useEffect(() => {
    if (activeTab === "feed") {
      feedBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, activeTab]);

  const toggleFolder = (folderKey: string) => {
    setExpandedFolders((prev) => ({
      ...prev,
      [folderKey]: !prev[folderKey],
    }));
  };

  const handleSubmitMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  const getAgentBadge = (sender: AgentSender) => {
    switch (sender) {
      case "queen":
        return {
          icon: <Crown size={12} className="text-amber-800" />,
          label: "Queen Bee",
          className: "agent-queen",
        };
      case "worker":
        return {
          icon: <Bot size={12} className="text-blue-800" />,
          label: "Worker Bee",
          className: "agent-worker",
        };
      case "scribe":
        return {
          icon: <Scroll size={12} className="text-purple-800" />,
          label: "Scribe Bee",
          className: "agent-scribe",
        };
      case "qa":
        return {
          icon: <FlaskConical size={12} className="text-emerald-800" />,
          label: "QA Bee",
          className: "agent-qa",
        };
      case "research":
        return {
          icon: <Sparkles size={12} className="text-cyan-800" />,
          label: "Research Bee",
          className: "agent-research",
        };
      case "system":
      default:
        return {
          icon: <User size={12} className="text-stone-700" />,
          label: "User / System",
          className: "agent-system",
        };
    }
  };

  const filteredMessages = messages.filter((msg) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      msg.content.toLowerCase().includes(q) ||
      msg.sender.toLowerCase().includes(q) ||
      msg.lane.toLowerCase().includes(q)
    );
  });

  return (
    <aside className={`retro-sidebar ${!isSidebarOpen ? "collapsed" : ""}`} aria-label="Sidebar">
      {/* Top Controls Header */}
      <div className="sidebar-top-bar">
        <button
          type="button"
          className="sidebar-icon-btn"
          onClick={onOpenSettings}
          title="Swarm Settings & System Config"
        >
          <Settings size={18} />
        </button>

        {/* View Switcher / Tabs */}
        <div className="sidebar-tabs">
          <button
            type="button"
            className={`sidebar-tab-btn ${activeTab === "feed" ? "active" : ""}`}
            onClick={() => setActiveTab("feed")}
            title="Live Nectar Chatter Feed"
          >
            <MessageSquare size={13} />
            <span>Nectar Feed</span>
            {messages.length > 0 && (
              <span className="tab-badge">{messages.length}</span>
            )}
          </button>
          <button
            type="button"
            className={`sidebar-tab-btn ${activeTab === "files" ? "active" : ""}`}
            onClick={() => setActiveTab("files")}
            title="Project File Explorer"
          >
            <Folder size={13} />
            <span>Files</span>
          </button>
        </div>

        <button
          type="button"
          className="sidebar-icon-btn sidebar-collapse-btn"
          onClick={onToggleSidebar}
          title="Toggle Sidebar (Collapse) [Ctrl+B]"
          aria-label="Toggle Sidebar"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="sidebar-content-area">
        {activeTab === "feed" ? (
          /* NECTAR LIVE FEED VIEW */
          <div className="nectar-feed-view">
            <div className="feed-status-strip">
              <span className="feed-title">
                NECTAR AGENT FEED
              </span>
              <span className="feed-count">{filteredMessages.length} updates</span>
            </div>

            {showSearchInput && (
              <div className="sidebar-search-row">
                <Search size={14} className="search-inline-icon" />
                <input
                  type="text"
                  className="sidebar-search-input"
                  placeholder="Filter messages or lane..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoFocus
                />
              </div>
            )}

            <div className="feed-messages-container">
              {filteredMessages.length === 0 ? (
                <div className="feed-empty-state">
                  <div className="feed-empty-icon">🐝</div>
                  <p className="feed-empty-title">Nectar Stream Idle</p>
                  <p className="feed-empty-sub">
                    Click "Run Demo" to watch Queen, Workers, Scribe and QA Bees message in real time.
                  </p>
                </div>
              ) : (
                filteredMessages.map((m) => {
                  const badge = getAgentBadge(m.sender);
                  const isUser = m.sender === "system" && m.content.startsWith("You:");
                  return (
                    <article
                      key={m.id}
                      className={`feed-bubble ${badge.className} ${isUser ? "feed-bubble-user" : ""}`}
                    >
                      <div className="feed-bubble-meta">
                        <span className="agent-tag">
                          {badge.icon}
                          <span className="agent-tag-text">{badge.label}</span>
                        </span>
                        {m.lane !== "none" && (
                          <span className={`lane-mini-tag lane-${m.lane.toLowerCase()}`}>
                            {m.lane}
                          </span>
                        )}
                      </div>
                      <p className="feed-bubble-content">{m.content}</p>
                      <span className="feed-bubble-time">
                        {new Date(m.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </article>
                  );
                })
              )}
              <div ref={feedBottomRef} />
            </div>

            {/* User Input Bar to send instructions to Queen */}
            <form onSubmit={handleSubmitMessage} className="feed-input-form">
              <input
                type="text"
                className="retro-feed-input"
                placeholder="Message Queen Bee or steer swarm..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />
              <button
                type="submit"
                className="retro-feed-send-btn"
                title="Send Instruction"
                disabled={!inputText.trim()}
              >
                <Send size={14} />
              </button>
            </form>
          </div>
        ) : (
          /* PROJECT EXPLORER VIEW (Exact match to design image) */
          <div className="project-tree-view">
            {/* Tree Root */}
            <div className="tree-root-header">
              <div
                className="tree-root-label"
                onClick={() => toggleFolder("project")}
              >
                {expandedFolders.project ? (
                  <ChevronDown size={14} className="tree-arrow" />
                ) : (
                  <ChevronRight size={14} className="tree-arrow" />
                )}
                <span className="tree-root-title">FINAL-PROJECT</span>
              </div>
              <div className="tree-root-actions">
                <button type="button" className="tree-action-btn" title="New File">
                  <Plus size={12} />
                </button>
                <button type="button" className="tree-action-btn" title="New Folder">
                  <FolderPlus size={12} />
                </button>
                <button type="button" className="tree-action-btn" title="Refresh">
                  <RefreshCw size={11} />
                </button>
              </div>
            </div>

            {/* Tree Items */}
            {expandedFolders.project && (
              <div className="tree-items-list">
                {/* frontend folder with green dot */}
                <div
                  className="tree-item folder-item"
                  onClick={() => toggleFolder("frontend")}
                >
                  <div className="tree-item-left">
                    {expandedFolders.frontend ? (
                      <ChevronDown size={13} className="tree-chevron" />
                    ) : (
                      <ChevronRight size={13} className="tree-chevron" />
                    )}
                    <Folder size={14} className="folder-icon text-amber-700" />
                    <span className="item-name font-medium">frontend</span>
                  </div>
                  <span className="folder-live-dot" title="Active development container" />
                </div>

                {/* Sub-items under frontend or root */}
                <div className="tree-item folder-item indent-1">
                  <ChevronRight size={13} className="tree-chevron" />
                  <Folder size={14} className="folder-icon text-stone-500" />
                  <span className="item-name text-stone-600">.vscode</span>
                </div>

                <div className="tree-item folder-item indent-1">
                  <ChevronRight size={13} className="tree-chevron" />
                  <Folder size={14} className="folder-icon text-stone-500" />
                  <span className="item-name text-stone-600">node_modules</span>
                </div>

                <div className="tree-item folder-item indent-1">
                  <ChevronRight size={13} className="tree-chevron" />
                  <Folder size={14} className="folder-icon text-stone-500" />
                  <span className="item-name text-stone-600">public</span>
                </div>

                {/* src folder (Selected highlight pill matching screenshot) */}
                <div
                  className={`tree-item folder-item selected-folder-pill indent-1`}
                  onClick={() => toggleFolder("src")}
                >
                  <div className="tree-item-left">
                    {expandedFolders.src ? (
                      <ChevronDown size={13} className="tree-chevron" />
                    ) : (
                      <ChevronRight size={13} className="tree-chevron" />
                    )}
                    <span className="src-code-tag">&lt;/&gt;</span>
                    <span className="item-name font-semibold">src</span>
                  </div>
                  <span className="src-active-ring" />
                </div>

                {/* Files under src */}
                {expandedFolders.src && (
                  <div className="src-files-list">
                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-text git-icon">&lt;</span>
                      <span className="item-name">.gitignore</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-text prettier-icon">P</span>
                      <span className="item-name">.prettierignore</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-text prettier-icon">P</span>
                      <span className="item-name">.prettierrc</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-text html-icon">5</span>
                      <span className="item-name">index.html</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <FileCheck size={13} className="json-icon" />
                      <span className="item-name">package-lock.json</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <FileCheck size={13} className="json-icon" />
                      <span className="item-name">package.json</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-dot red-dot" />
                      <span className="item-name">postcss.config.cjs</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-text info-icon">i</span>
                      <span className="item-name">README.md</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-text tailwind-icon">≈</span>
                      <span className="item-name">tailwind.config.cjs</span>
                    </div>

                    <div className="tree-item file-item indent-2">
                      <span className="file-badge-text vite-icon">⚡</span>
                      <span className="item-name">vite.config.js</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Profile Bar (Exact match to design screenshot) */}
      <div className="sidebar-bottom-bar">
        <div className="user-profile-pill">
          <div className="user-avatar-circle">
            <span role="img" aria-label="avatar">
              🧑‍💻
            </span>
          </div>
          <span className="user-profile-name">User1</span>
        </div>

        <button
          type="button"
          className="sidebar-search-btn"
          onClick={() => {
            if (activeTab !== "feed") setActiveTab("feed");
            setShowSearchInput((prev) => !prev);
          }}
          title="Search chatter or files"
        >
          <Search size={16} />
        </button>
      </div>
    </aside>
  );
};
