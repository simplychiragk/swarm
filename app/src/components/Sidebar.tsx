import React, { useState, useRef, useEffect } from "react";
import type { FeedMessage, AgentSender } from "../types/contracts";
import type { ProjectFile } from "./FileViewerModal";
import {
  Settings,
  PanelLeftClose,
  Folder,
  FolderOpen,
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
  FileCode,
  FileText,
  Check,
  X,
} from "lucide-react";

interface SidebarProps {
  messages: FeedMessage[];
  onSendMessage: (text: string) => void;
  onOpenSettings: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onOpenFile: (file: ProjectFile) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  messages,
  onSendMessage,
  onOpenSettings,
  isSidebarOpen,
  onToggleSidebar,
  onOpenFile,
}) => {
  const [activeTab, setActiveTab] = useState<"feed" | "files">("feed");
  const [inputText, setInputText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchInput, setShowSearchInput] = useState(false);

  // Folder toggle states
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    project: true,
    frontend: true,
    vscode: false,
    node_modules: false,
    public: false,
    src: true,
  });

  // Dynamic file list and creation state
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newItemName, setNewItemName] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedFilePath, setSelectedFilePath] = useState<string>("frontend/src/index.html");
  const [sidebarToast, setSidebarToast] = useState<string | null>(null);

  const feedBottomRef = useRef<HTMLDivElement | null>(null);
  const newFileInputRef = useRef<HTMLInputElement | null>(null);

  // Auto-scroll feed to bottom when new messages arrive
  useEffect(() => {
    if (activeTab === "feed") {
      feedBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, activeTab]);

  // Focus input when creating new file/folder
  useEffect(() => {
    if (isCreatingFile || isCreatingFolder) {
      newFileInputRef.current?.focus();
    }
  }, [isCreatingFile, isCreatingFolder]);

  const showToast = (msg: string) => {
    setSidebarToast(msg);
    setTimeout(() => {
      setSidebarToast(null);
    }, 2400);
  };

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

  // Base starter files map
  const [filesMap, setFilesMap] = useState<Record<string, ProjectFile>>({
    ".gitignore": {
      name: ".gitignore",
      path: "frontend/src/.gitignore",
      language: "gitignore",
      content: `# Dependencies\nnode_modules/\n.pnpm-store/\n\n# Build outputs\ndist/\nbuild/\napp/dist/\n\n# Environment & Secrets\n.env\n.env.local\n*.key\n*.pem\n\n# OS & IDE\n.DS_Store\nThumbs.db\n*.log`,
    },
    ".prettierignore": {
      name: ".prettierignore",
      path: "frontend/src/.prettierignore",
      language: "ignore",
      content: `node_modules\ndist\npackage-lock.json\n*.min.js\n*.min.css`,
    },
    ".prettierrc": {
      name: ".prettierrc",
      path: "frontend/src/.prettierrc",
      language: "json",
      content: `{\n  "semi": true,\n  "tabWidth": 2,\n  "singleQuote": false,\n  "trailingComma": "es5"\n}`,
    },
    "index.html": {
      name: "index.html",
      path: "frontend/src/index.html",
      language: "html",
      content: `<!doctype html>\n<html lang="en">\n  <head>\n    <meta charset="UTF-8" />\n    <link rel="icon" type="image/svg+xml" href="/vite.svg" />\n    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n    <title>Swarm • Honeycomb Workspace</title>\n  </head>\n  <body>\n    <div id="root"></div>\n    <script type="module" src="/src/main.tsx"></script>\n  </body>\n</html>`,
    },
    "package-lock.json": {
      name: "package-lock.json",
      path: "frontend/src/package-lock.json",
      language: "json",
      content: `{\n  "name": "swarm-client",\n  "version": "0.1.0",\n  "lockfileVersion": 3,\n  "requires": true,\n  "packages": {\n    "": {\n      "name": "swarm-client",\n      "version": "0.1.0"\n    }\n  }\n}`,
    },
    "package.json": {
      name: "package.json",
      path: "frontend/src/package.json",
      language: "json",
      content: `{\n  "name": "swarm-app",\n  "private": true,\n  "version": "0.1.0",\n  "type": "module",\n  "scripts": {\n    "dev": "vite",\n    "build": "tsc && vite build",\n    "tauri": "tauri"\n  },\n  "dependencies": {\n    "react": "^19.1.0",\n    "react-dom": "^19.1.0",\n    "lucide-react": "^1.16.0",\n    "@tauri-apps/api": "^2"\n  }\n}`,
    },
    "postcss.config.cjs": {
      name: "postcss.config.cjs",
      path: "frontend/src/postcss.config.cjs",
      language: "javascript",
      content: `module.exports = {\n  plugins: {\n    tailwindcss: {},\n    autoprefixer: {},\n  },\n};`,
    },
    "README.md": {
      name: "README.md",
      path: "frontend/src/README.md",
      language: "markdown",
      content: `# Swarm: Multi-Agent AI Coding Platform\n\nA desktop application where a multi-agent AI coding swarm builds with you in real time.\n\n- **Queen Bee**: Interviews user, plans tasks, delegator\n- **Workers**: FE, BE, DB, Design, Test, Docs\n- **Scribe**: Summarizes chatter into Honeycomb whiteboard\n- **TinyFish**: Live web research before building, and automated real-browser QA with evidence\n- **Decision Layer (Jev)**: Rule-based routing and human-in-the-loop authorization gates.`,
    },
    "tailwind.config.cjs": {
      name: "tailwind.config.cjs",
      path: "frontend/src/tailwind.config.cjs",
      language: "javascript",
      content: `/** @type {import('tailwindcss').Config} */\nmodule.exports = {\n  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],\n  theme: {\n    extend: {\n      colors: {\n        honey: "#E5A12D",\n        "honey-dark": "#C57E12",\n        canvas: "#FBF6E9",\n      },\n    },\n  },\n  plugins: [],\n};`,
    },
    "vite.config.js": {
      name: "vite.config.js",
      path: "frontend/src/vite.config.js",
      language: "javascript",
      content: `import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\n\nexport default defineConfig({\n  plugins: [react()],\n  server: {\n    port: 1420,\n    strictPort: true,\n  },\n});`,
    },
  });

  // Additional custom subfolders created by user
  const [customFolders, setCustomFolders] = useState<string[]>([]);

  // List of filenames under src
  const srcFileNames = Object.keys(filesMap).filter((k) =>
    filesMap[k].path.startsWith("frontend/src/")
  );

  const handleSelectFile = (fileName: string) => {
    const file = filesMap[fileName];
    if (file) {
      setSelectedFilePath(file.path);
      onOpenFile(file);
    }
  };

  const handleConfirmNewItem = () => {
    const trimmed = newItemName.trim();
    if (!trimmed) {
      setIsCreatingFile(false);
      setIsCreatingFolder(false);
      return;
    }

    if (isCreatingFile) {
      // Determine language and boilerplate
      let lang = "typescript";
      let content = `// ${trimmed}\n\nexport const Component = () => {\n  return <div>${trimmed}</div>;\n};\n`;

      if (trimmed.endsWith(".json")) {
        lang = "json";
        content = `{\n  "name": "${trimmed.replace(".json", "")}"\n}`;
      } else if (trimmed.endsWith(".css")) {
        lang = "css";
        content = `/* ${trimmed} */\n.container {\n  padding: 16px;\n}\n`;
      } else if (trimmed.endsWith(".html")) {
        lang = "html";
        content = `<!doctype html>\n<html>\n  <body>\n    <h1>${trimmed}</h1>\n  </body>\n</html>`;
      } else if (trimmed.endsWith(".md")) {
        lang = "markdown";
        content = `# ${trimmed}\n\nDocument details here.\n`;
      }

      const newFile: ProjectFile = {
        name: trimmed,
        path: `frontend/src/${trimmed}`,
        language: lang,
        content,
      };

      setFilesMap((prev) => ({
        ...prev,
        [trimmed]: newFile,
      }));

      setSelectedFilePath(newFile.path);
      setIsCreatingFile(false);
      setNewItemName("");

      // Sync to backend workspace
      fetch("http://127.0.0.1:8000/workspace/files", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: `src/${trimmed}`,
          content,
          is_directory: false,
        }),
      }).catch((e) => console.warn("Could not sync file to backend:", e));

      showToast(`Created file: ${trimmed}`);
      onOpenFile(newFile);
    } else if (isCreatingFolder) {
      setCustomFolders((prev) => (prev.includes(trimmed) ? prev : [...prev, trimmed]));
      setExpandedFolders((prev) => ({ ...prev, [trimmed]: true }));
      setIsCreatingFolder(false);
      setNewItemName("");

      fetch("http://127.0.0.1:8000/workspace/files", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: `src/${trimmed}`,
          is_directory: true,
        }),
      }).catch((e) => console.warn("Could not sync folder to backend:", e));

      showToast(`Created folder: ${trimmed}`);
    }
  };

  const fetchWorkspaceTree = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/workspace/tree");
      if (res.ok) {
        const data = await res.json();
        if (data.files && Array.isArray(data.files) && data.files.length > 0) {
          const newMap: Record<string, ProjectFile> = {};
          for (const f of data.files) {
            const displayPath = f.path.startsWith("src/")
              ? `frontend/${f.path}`
              : `frontend/src/${f.path}`;
            newMap[f.name] = {
              name: f.name,
              path: displayPath,
              language: f.language,
              content: f.content,
            };
          }
          setFilesMap((prev) => ({ ...prev, ...newMap }));
        }
      }
    } catch {
      // offline/mock fallback
    }
  };

  useEffect(() => {
    fetchWorkspaceTree();
  }, []);

  const handleRefreshTree = async () => {
    setIsRefreshing(true);
    setExpandedFolders({
      project: true,
      frontend: true,
      vscode: true,
      node_modules: false,
      public: true,
      src: true,
    });
    await fetchWorkspaceTree();
    setIsRefreshing(false);
    showToast("Files refreshed from workspace");
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

      {/* Floating feedback toast */}
      {sidebarToast && (
        <div className="sidebar-feedback-toast" role="status">
          <Check size={12} />
          <span>{sidebarToast}</span>
        </div>
      )}

      {/* Main Content Area */}
      <div className="sidebar-content-area">
        {activeTab === "feed" ? (
          /* NECTAR LIVE FEED VIEW */
          <div className="nectar-feed-view">
            <div className="feed-status-strip">
              <span className="feed-title">NECTAR AGENT FEED</span>
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
          /* PROJECT EXPLORER VIEW (Full interactive files tree) */
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

              {/* Functional Action Icons: New File, New Folder, Refresh */}
              <div className="tree-root-actions">
                <button
                  type="button"
                  className="tree-action-btn"
                  title="New File (in src)"
                  onClick={() => {
                    setIsCreatingFolder(false);
                    setIsCreatingFile(true);
                    setNewItemName("");
                    if (!expandedFolders.src) {
                      setExpandedFolders((p) => ({ ...p, src: true }));
                    }
                  }}
                >
                  <Plus size={13} />
                </button>

                <button
                  type="button"
                  className="tree-action-btn"
                  title="New Folder"
                  onClick={() => {
                    setIsCreatingFile(false);
                    setIsCreatingFolder(true);
                    setNewItemName("");
                  }}
                >
                  <FolderPlus size={13} />
                </button>

                <button
                  type="button"
                  className={`tree-action-btn ${isRefreshing ? "spin-icon" : ""}`}
                  title="Refresh File Tree"
                  onClick={handleRefreshTree}
                >
                  <RefreshCw size={12} />
                </button>
              </div>
            </div>

            {/* Inline creation form for new file or folder */}
            {(isCreatingFile || isCreatingFolder) && (
              <div className="tree-inline-create-box">
                <div className="inline-create-header">
                  {isCreatingFile ? (
                    <>
                      <FileCode size={13} className="text-amber-800" />
                      <span>New File in src/</span>
                    </>
                  ) : (
                    <>
                      <Folder size={13} className="text-amber-800" />
                      <span>New Folder</span>
                    </>
                  )}
                </div>
                <div className="inline-create-input-row">
                  <input
                    ref={newFileInputRef}
                    type="text"
                    className="inline-create-input"
                    placeholder={isCreatingFile ? "e.g. Header.tsx, style.css" : "e.g. components, utils"}
                    value={newItemName}
                    onChange={(e) => setNewItemName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleConfirmNewItem();
                      if (e.key === "Escape") {
                        setIsCreatingFile(false);
                        setIsCreatingFolder(false);
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="inline-submit-btn check-btn"
                    onClick={handleConfirmNewItem}
                    title="Confirm (Enter)"
                  >
                    <Check size={12} />
                  </button>
                  <button
                    type="button"
                    className="inline-submit-btn cancel-btn"
                    onClick={() => {
                      setIsCreatingFile(false);
                      setIsCreatingFolder(false);
                    }}
                    title="Cancel (Esc)"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            )}

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
                    {expandedFolders.frontend ? (
                      <FolderOpen size={14} className="folder-icon text-amber-700" />
                    ) : (
                      <Folder size={14} className="folder-icon text-amber-700" />
                    )}
                    <span className="item-name font-medium">frontend</span>
                  </div>
                  <span className="folder-live-dot" title="Active development container" />
                </div>

                {expandedFolders.frontend && (
                  <>
                    {/* .vscode folder */}
                    <div
                      className="tree-item folder-item indent-1"
                      onClick={() => toggleFolder("vscode")}
                    >
                      <div className="tree-item-left">
                        {expandedFolders.vscode ? (
                          <ChevronDown size={13} className="tree-chevron" />
                        ) : (
                          <ChevronRight size={13} className="tree-chevron" />
                        )}
                        <Folder size={14} className="folder-icon text-stone-500" />
                        <span className="item-name text-stone-600">.vscode</span>
                      </div>
                    </div>

                    {expandedFolders.vscode && (
                      <div className="vscode-files-list">
                        <div
                          className="tree-item file-item indent-2"
                          onClick={() =>
                            onOpenFile({
                              name: "settings.json",
                              path: "frontend/.vscode/settings.json",
                              language: "json",
                              content: `{\n  "editor.formatOnSave": true,\n  "editor.defaultFormatter": "esbenp.prettier-vscode",\n  "typescript.tsdk": "node_modules/typescript/lib"\n}`,
                            })
                          }
                        >
                          <FileCheck size={13} className="json-icon" />
                          <span className="item-name">settings.json</span>
                        </div>
                        <div
                          className="tree-item file-item indent-2"
                          onClick={() =>
                            onOpenFile({
                              name: "extensions.json",
                              path: "frontend/.vscode/extensions.json",
                              language: "json",
                              content: `{\n  "recommendations": [\n    "dbaeumer.vscode-eslint",\n    "esbenp.prettier-vscode",\n    "bradlc.vscode-tailwindcss"\n  ]\n}`,
                            })
                          }
                        >
                          <FileCheck size={13} className="json-icon" />
                          <span className="item-name">extensions.json</span>
                        </div>
                      </div>
                    )}

                    {/* node_modules folder */}
                    <div
                      className="tree-item folder-item indent-1"
                      onClick={() => toggleFolder("node_modules")}
                    >
                      <div className="tree-item-left">
                        {expandedFolders.node_modules ? (
                          <ChevronDown size={13} className="tree-chevron" />
                        ) : (
                          <ChevronRight size={13} className="tree-chevron" />
                        )}
                        <Folder size={14} className="folder-icon text-stone-500" />
                        <span className="item-name text-stone-600">node_modules</span>
                      </div>
                      <span className="node-modules-count">28 pkgs</span>
                    </div>

                    {expandedFolders.node_modules && (
                      <div className="node-modules-list">
                        <div className="tree-item file-item indent-2 opacity-75">
                          <span className="file-badge-text font-mono">📦</span>
                          <span className="item-name">@tauri-apps/api</span>
                        </div>
                        <div className="tree-item file-item indent-2 opacity-75">
                          <span className="file-badge-text font-mono">📦</span>
                          <span className="item-name">lucide-react</span>
                        </div>
                        <div className="tree-item file-item indent-2 opacity-75">
                          <span className="file-badge-text font-mono">📦</span>
                          <span className="item-name">react</span>
                        </div>
                        <div className="tree-item file-item indent-2 opacity-75">
                          <span className="file-badge-text font-mono">📦</span>
                          <span className="item-name">tailwindcss</span>
                        </div>
                      </div>
                    )}

                    {/* public folder */}
                    <div
                      className="tree-item folder-item indent-1"
                      onClick={() => toggleFolder("public")}
                    >
                      <div className="tree-item-left">
                        {expandedFolders.public ? (
                          <ChevronDown size={13} className="tree-chevron" />
                        ) : (
                          <ChevronRight size={13} className="tree-chevron" />
                        )}
                        <Folder size={14} className="folder-icon text-stone-500" />
                        <span className="item-name text-stone-600">public</span>
                      </div>
                    </div>

                    {expandedFolders.public && (
                      <div className="public-files-list">
                        <div
                          className="tree-item file-item indent-2"
                          onClick={() =>
                            onOpenFile({
                              name: "tauri.svg",
                              path: "frontend/public/tauri.svg",
                              language: "svg",
                              content: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n  <circle cx="50" cy="50" r="40" fill="#24C8DB"/>\n</svg>`,
                            })
                          }
                        >
                          <span className="file-badge-text font-mono text-cyan-600">❖</span>
                          <span className="item-name">tauri.svg</span>
                        </div>
                        <div
                          className="tree-item file-item indent-2"
                          onClick={() =>
                            onOpenFile({
                              name: "vite.svg",
                              path: "frontend/public/vite.svg",
                              language: "svg",
                              content: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n  <polygon points="50,10 90,90 10,90" fill="#FFC93C"/>\n</svg>`,
                            })
                          }
                        >
                          <span className="file-badge-text vite-icon">⚡</span>
                          <span className="item-name">vite.svg</span>
                        </div>
                      </div>
                    )}

                    {/* Custom User Folders */}
                    {customFolders.map((cFolder) => (
                      <div
                        key={cFolder}
                        className="tree-item folder-item indent-1"
                        onClick={() => toggleFolder(cFolder)}
                      >
                        <div className="tree-item-left">
                          {expandedFolders[cFolder] ? (
                            <ChevronDown size={13} className="tree-chevron" />
                          ) : (
                            <ChevronRight size={13} className="tree-chevron" />
                          )}
                          <Folder size={14} className="folder-icon text-amber-600" />
                          <span className="item-name font-medium">{cFolder}</span>
                        </div>
                      </div>
                    ))}

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
                        {srcFileNames.map((fileName) => {
                          const file = filesMap[fileName];
                          const isSelected = selectedFilePath === file.path;

                          let badgeIcon = <FileText size={13} className="text-stone-500" />;

                          if (fileName.includes("git")) {
                            badgeIcon = <span className="file-badge-text git-icon">&lt;</span>;
                          } else if (fileName.includes("prettier")) {
                            badgeIcon = <span className="file-badge-text prettier-icon">P</span>;
                          } else if (fileName.endsWith(".html")) {
                            badgeIcon = <span className="file-badge-text html-icon">5</span>;
                          } else if (fileName.endsWith(".json")) {
                            badgeIcon = <FileCheck size={13} className="json-icon" />;
                          } else if (fileName.includes("postcss")) {
                            badgeIcon = <span className="file-badge-dot red-dot" />;
                          } else if (fileName.endsWith(".md")) {
                            badgeIcon = <span className="file-badge-text info-icon">i</span>;
                          } else if (fileName.includes("tailwind")) {
                            badgeIcon = <span className="file-badge-text tailwind-icon">≈</span>;
                          } else if (fileName.includes("vite")) {
                            badgeIcon = <span className="file-badge-text vite-icon">⚡</span>;
                          } else if (fileName.endsWith(".tsx") || fileName.endsWith(".ts")) {
                            badgeIcon = <span className="file-badge-text text-blue-700 font-bold">TS</span>;
                          } else if (fileName.endsWith(".css")) {
                            badgeIcon = <span className="file-badge-text text-cyan-700 font-bold">#</span>;
                          }

                          return (
                            <div
                              key={fileName}
                              className={`tree-item file-item indent-2 ${
                                isSelected ? "selected-file-pill" : ""
                              }`}
                              onClick={() => handleSelectFile(fileName)}
                              title={`Click to preview code: ${fileName}`}
                            >
                              <div className="tree-item-left">
                                {badgeIcon}
                                <span className="item-name">{fileName}</span>
                              </div>
                              {isSelected && <span className="file-view-indicator">View</span>}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
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
