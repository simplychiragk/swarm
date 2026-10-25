import React, { useState, useRef, useEffect, useMemo } from "react";
import type { FeedMessage, AgentSender } from "../types/contracts";
import type { ProjectFile } from "./FileViewerModal";
import {
  Settings,
  PanelLeftClose,
  Folder,
  FolderOpen,
  ChevronDown,
  ChevronRight,
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
  FolderUp,
  ExternalLink,
  HardDrive,
  FileCode,
  FileText,
  Check,
  X,
  Copy,
} from "lucide-react";

export interface StarterGoal {
  icon: string;
  title: string;
  prompt: string;
}

export const STARTER_GOALS: StarterGoal[] = [
  {
    icon: "🐝",
    title: "Developer Tools Waitlist",
    prompt: "Build a developer tools waitlist landing page with dark honeycomb aesthetic, capturing name, email, and role.",
  },
  {
    icon: "🚀",
    title: "SaaS Early Access Portal",
    prompt: "Create a SaaS early access landing page with live countdown, feature highlights, and GitHub sign-up.",
  },
  {
    icon: "📊",
    title: "Analytics Dashboard Waitlist",
    prompt: "Generate an analytics dashboard waitlist with early access token generation and tier preview.",
  },
];

interface SidebarProps {
  messages: FeedMessage[];
  onSendMessage: (text: string) => void;
  onResetBoard?: () => void;
  onOpenSettings: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onOpenFile: (file: ProjectFile) => void;
}

interface FileTreeNode {
  name: string;
  fullPath: string;
  isFolder: boolean;
  children: Record<string, FileTreeNode>;
  file?: ProjectFile;
}

function buildFileTree(files: Record<string, ProjectFile>): FileTreeNode {
  const root: FileTreeNode = {
    name: "root",
    fullPath: "",
    isFolder: true,
    children: {},
  };

  const sortedPaths = Object.keys(files).sort();

  for (const pathKey of sortedPaths) {
    const file = files[pathKey];
    const clean = file.path.replace(/\\/g, "/").replace(/^\/+/, "");
    const parts = clean.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const currentPath = parts.slice(0, i + 1).join("/");

      if (isLast) {
        current.children[part] = {
          name: part,
          fullPath: currentPath,
          isFolder: false,
          children: {},
          file,
        };
      } else {
        if (!current.children[part]) {
          current.children[part] = {
            name: part,
            fullPath: currentPath,
            isFolder: true,
            children: {},
          };
        }
        current = current.children[part];
      }
    }
  }

  return root;
}

export const Sidebar: React.FC<SidebarProps> = ({
  messages,
  onSendMessage,
  onResetBoard,
  onOpenSettings,
  isSidebarOpen,
  onToggleSidebar,
  onOpenFile,
}) => {
  const [activeTab, setActiveTab] = useState<"feed" | "files">("feed");
  const [inputText, setInputText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchInput, setShowSearchInput] = useState(false);

  // Live Working Directory State
  const [workspacePath, setWorkspacePath] = useState<string>("");
  const [workspaceName, setWorkspaceName] = useState<string>("workspace");
  const [openedFolderName, setOpenedFolderName] = useState<string | null>(null);
  const [isLocalFolderOverride, setIsLocalFolderOverride] = useState(false);

  // Files map keyed by file.path (e.g. "index.html", "src/App.tsx", "api/main.py")
  const [filesMap, setFilesMap] = useState<Record<string, ProjectFile>>({});

  // Dynamic folder expansion state (folderPath -> boolean)
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    __root__: true,
  });

  // Dynamic file list and creation state
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newItemName, setNewItemName] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedFilePath, setSelectedFilePath] = useState<string>("");
  const [sidebarToast, setSidebarToast] = useState<string | null>(null);

  // Open Directory Modal state
  const [showOpenDirModal, setShowOpenDirModal] = useState(false);
  const [targetDirPath, setTargetDirPath] = useState("");
  const [isSwitchingDir, setIsSwitchingDir] = useState(false);

  // Desktop folder opening & popover state
  const [showFolderMenu, setShowFolderMenu] = useState(false);
  const folderMenuRef = useRef<HTMLDivElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

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

  // Close folder menu on click outside or Escape
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (
        folderMenuRef.current &&
        !folderMenuRef.current.contains(e.target as Node)
      ) {
        setShowFolderMenu(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showOpenDirModal) setShowOpenDirModal(false);
        if (showFolderMenu) setShowFolderMenu(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [showFolderMenu, showOpenDirModal]);

  const showToast = (msg: string) => {
    setSidebarToast(msg);
    setTimeout(() => {
      setSidebarToast(null);
    }, 2400);
  };

  const toggleFolder = (folderKey: string) => {
    setExpandedFolders((prev) => {
      const isCurrentlyExpanded = prev[folderKey] !== false; // default true
      return {
        ...prev,
        [folderKey]: !isCurrentlyExpanded,
      };
    });
  };

  // Real-time workspace tree fetch from sidecar
  const fetchWorkspaceTree = async () => {
    // If user is currently browsing an offline custom folder, don't wipe it out
    if (isLocalFolderOverride) return;

    try {
      const res = await fetch("http://127.0.0.1:8000/workspace/tree");
      if (res.ok) {
        const data = await res.json();
        if (data.workspace) {
          setWorkspacePath(data.workspace);
          const normalized = data.workspace.replace(/\\/g, "/").replace(/\/$/, "");
          const folderName = normalized.split("/").pop() || "workspace";
          setWorkspaceName(folderName);
        }
        if (data.files && Array.isArray(data.files) && data.files.length > 0) {
          const newMap: Record<string, ProjectFile> = {};
          for (const f of data.files) {
            newMap[f.path] = {
              name: f.name,
              path: f.path,
              language: f.language,
              content: f.content,
            };
          }
          setFilesMap(newMap);

          if (!selectedFilePath && data.files[0]) {
            setSelectedFilePath(data.files[0].path);
          }
        }
      }
    } catch {
      // offline/mock fallback
    }
  };

  // Fetch workspace on initial mount
  useEffect(() => {
    fetchWorkspaceTree();
  }, []);

  // Sync workspace tree in real time whenever messages arrive
  useEffect(() => {
    fetchWorkspaceTree();
  }, [messages.length]);

  // Periodic poll every 4 seconds when Files tab is active
  useEffect(() => {
    if (activeTab === "files" && !isLocalFolderOverride) {
      const timer = setInterval(fetchWorkspaceTree, 4000);
      return () => clearInterval(timer);
    }
  }, [activeTab, isLocalFolderOverride]);

  const handleRefreshTree = async () => {
    setIsRefreshing(true);
    setIsLocalFolderOverride(false);
    setOpenedFolderName(null);
    await fetchWorkspaceTree();
    setIsRefreshing(false);
    showToast(`Workspace refreshed (${Object.keys(filesMap).length} files)`);
  };

  // Open directory via sidecar POST /workspace/open (Gap 1 External Project Mode)
  const handleOpenDirectoryPath = async (dirToOpen: string) => {
    setIsSwitchingDir(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/workspace/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: dirToOpen.trim() }),
      });

      if (res.ok) {
        const data = await res.json();
        setIsLocalFolderOverride(false);
        setOpenedFolderName(null);

        if (data.workspace) {
          setWorkspacePath(data.workspace);
          const normalized = data.workspace.replace(/\\/g, "/").replace(/\/$/, "");
          const folderName = normalized.split("/").pop() || "workspace";
          setWorkspaceName(folderName);
        }

        const newMap: Record<string, ProjectFile> = {};
        if (data.files && Array.isArray(data.files)) {
          for (const f of data.files) {
            newMap[f.path] = {
              name: f.name,
              path: f.path,
              language: f.language,
              content: f.content,
            };
          }
        }
        setFilesMap(newMap);
        setShowOpenDirModal(false);
        setTargetDirPath("");
        setActiveTab("files");

        if (dirToOpen.trim()) {
          showToast(`Opened directory "${workspaceName}" (${data.count} files)`);
        } else {
          showToast("Reset to default sandbox workspace");
        }
      } else {
        const err = await res.json().catch(() => ({ detail: "Directory not found" }));
        showToast(`Failed to open: ${err.detail || "Directory does not exist"}`);
      }
    } catch (e) {
      console.error("Failed to switch workspace directory:", e);
      showToast("Could not connect to sidecar to open directory");
    } finally {
      setIsSwitchingDir(false);
    }
  };

  // Open existing folder on Desktop using native browser directory picker or fallback
  const handleBrowseDesktopFolder = async () => {
    setShowFolderMenu(false);

    if ("showDirectoryPicker" in window) {
      try {
        // @ts-expect-error - Chromium / WebView2 File System Access API
        const dirHandle = await window.showDirectoryPicker({
          id: "swarm-desktop-picker",
          startIn: "desktop",
        });

        const rootName = dirHandle.name;
        const newFiles: Record<string, ProjectFile> = {};
        let count = 0;

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const readEntries = async (handle: any, currentPath: string) => {
          if (count >= 300) return;
          for await (const entry of handle.values()) {
            if (count >= 300) break;
            const entryPath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
            if (entry.kind === "file") {
              if (
                entry.name.startsWith(".") ||
                /\.(png|jpg|jpeg|ico|gif|exe|dll|zip|tar|gz|woff|woff2)$/i.test(entry.name)
              ) {
                continue;
              }
              try {
                const file = await entry.getFile();
                if (file.size <= 500 * 1024) {
                  const text = await file.text();
                  const ext = entry.name.split(".").pop()?.toLowerCase() || "";
                  let lang = "text";
                  if (ext === "ts" || ext === "tsx") lang = "typescript";
                  else if (ext === "js" || ext === "jsx") lang = "javascript";
                  else if (ext === "json") lang = "json";
                  else if (ext === "html") lang = "html";
                  else if (ext === "css") lang = "css";
                  else if (ext === "md") lang = "markdown";
                  else if (ext === "py") lang = "python";
                  else if (ext === "rs") lang = "rust";
                  else if (ext === "toml") lang = "toml";

                  newFiles[entryPath] = {
                    name: entry.name,
                    path: entryPath,
                    language: lang,
                    content: text,
                  };
                  count++;
                }
              } catch {
                // Ignore unreadable file
              }
            } else if (entry.kind === "directory") {
              if (
                entry.name !== "node_modules" &&
                entry.name !== ".git" &&
                entry.name !== "dist" &&
                entry.name !== "build" &&
                !entry.name.startsWith(".")
              ) {
                await readEntries(entry, entryPath);
              }
            }
          }
        };

        await readEntries(dirHandle, "");

        if (count > 0) {
          setIsLocalFolderOverride(true);
          setFilesMap(newFiles);
          setOpenedFolderName(rootName);
          setActiveTab("files");
          showToast(`Opened folder "${rootName}" (${count} files)`);
          return;
        }
      } catch (err: unknown) {
        if ((err as Error)?.name === "AbortError") {
          return;
        }
        console.warn("Directory picker error, opening path dialog:", err);
      }
    }

    // Open directory path modal directly for guaranteed path entry
    setShowOpenDirModal(true);
  };

  // HTML5 folder selection change handler
  const handleFolderInputSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const newFiles: Record<string, ProjectFile> = {};
    let rootDirName = "Desktop Project";

    const firstPath = fileList[0].webkitRelativePath || "";
    if (firstPath) {
      const parts = firstPath.split("/");
      if (parts.length > 0 && parts[0]) {
        rootDirName = parts[0];
      }
    }

    let count = 0;
    for (let i = 0; i < fileList.length && count < 300; i++) {
      const file = fileList[i];
      if (file.size > 500 * 1024) continue;
      if (file.webkitRelativePath.includes("/.git/")) continue;
      if (file.webkitRelativePath.includes("/node_modules/")) continue;
      if (file.webkitRelativePath.includes("/dist/")) continue;
      if (/\.(png|jpg|jpeg|gif|ico|webp|exe|dll|zip|tar|gz|woff|woff2)$/i.test(file.name)) continue;

      try {
        const text = await file.text();
        const ext = file.name.split(".").pop()?.toLowerCase() || "";
        let lang = "text";
        if (ext === "ts" || ext === "tsx") lang = "typescript";
        else if (ext === "js" || ext === "jsx") lang = "javascript";
        else if (ext === "json") lang = "json";
        else if (ext === "html") lang = "html";
        else if (ext === "css") lang = "css";
        else if (ext === "md") lang = "markdown";
        else if (ext === "py") lang = "python";
        else if (ext === "rs") lang = "rust";
        else if (ext === "toml") lang = "toml";

        let rel = file.webkitRelativePath || file.name;
        if (rel.startsWith(rootDirName + "/")) {
          rel = rel.substring(rootDirName.length + 1);
        }

        newFiles[rel] = {
          name: file.name,
          path: rel,
          language: lang,
          content: text,
        };
        count++;
      } catch (err) {
        console.warn("Could not read file:", file.name, err);
      }
    }

    if (count > 0) {
      setIsLocalFolderOverride(true);
      setFilesMap(newFiles);
      setOpenedFolderName(rootDirName);
      setActiveTab("files");
      showToast(`Opened folder "${rootDirName}" (${count} files)`);
    } else {
      showToast(`Opened folder "${rootDirName}"`);
    }

    e.target.value = "";
    setShowFolderMenu(false);
  };

  // Open working directory in Windows File Explorer via Tauri opener
  const handleOpenInSystemExplorer = async () => {
    setShowFolderMenu(false);
    const isTauri = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
    const targetPath = workspacePath || "";

    if (isTauri && targetPath) {
      try {
        const { openPath } = await import("@tauri-apps/plugin-opener");
        await openPath(targetPath);
        showToast("Opened working directory in File Explorer");
        return;
      } catch (err) {
        console.error("Tauri openPath failed:", err);
      }
    }

    if (targetPath) {
      navigator.clipboard.writeText(targetPath);
      showToast(`Copied CWD path: ${targetPath}`);
    } else {
      setShowOpenDirModal(true);
    }
  };

  const handleSelectFile = (file: ProjectFile) => {
    setSelectedFilePath(file.path);
    onOpenFile(file);
  };

  const handleConfirmNewItem = async () => {
    const trimmed = newItemName.trim();
    if (!trimmed) {
      setIsCreatingFile(false);
      setIsCreatingFolder(false);
      return;
    }

    const cleanPath = trimmed.replace(/^[/\\]+/, "");

    if (isCreatingFile) {
      let lang = "typescript";
      let content = `// ${cleanPath}\n`;

      if (cleanPath.endsWith(".py")) {
        lang = "python";
        content = `# ${cleanPath}\n`;
      } else if (cleanPath.endsWith(".json")) {
        lang = "json";
        content = `{\n  "name": "${cleanPath.replace(".json", "")}"\n}\n`;
      } else if (cleanPath.endsWith(".css")) {
        lang = "css";
        content = `/* ${cleanPath} */\n`;
      } else if (cleanPath.endsWith(".html")) {
        lang = "html";
        content = `<!doctype html>\n<html>\n  <body>\n    <h1>${cleanPath}</h1>\n  </body>\n</html>\n`;
      } else if (cleanPath.endsWith(".md")) {
        lang = "markdown";
        content = `# ${cleanPath}\n`;
      }

      const newFile: ProjectFile = {
        name: cleanPath.split("/").pop() || cleanPath,
        path: cleanPath,
        language: lang,
        content,
      };

      setFilesMap((prev) => ({
        ...prev,
        [cleanPath]: newFile,
      }));

      setSelectedFilePath(cleanPath);
      setIsCreatingFile(false);
      setNewItemName("");

      try {
        await fetch("http://127.0.0.1:8000/workspace/files", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            path: cleanPath,
            content,
            is_directory: false,
          }),
        });
        showToast(`Created file: ${cleanPath}`);
        await fetchWorkspaceTree();
        onOpenFile(newFile);
      } catch (e) {
        console.warn("Could not sync file to backend:", e);
      }
    } else if (isCreatingFolder) {
      setExpandedFolders((prev) => ({ ...prev, [cleanPath]: true }));
      setIsCreatingFolder(false);
      setNewItemName("");

      try {
        await fetch("http://127.0.0.1:8000/workspace/files", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            path: cleanPath,
            is_directory: true,
          }),
        });
        showToast(`Created folder: ${cleanPath}`);
        await fetchWorkspaceTree();
      } catch (e) {
        console.warn("Could not sync folder to backend:", e);
      }
    }
  };

  const handleSubmitMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  // Build the hierarchical tree from the live files map
  const treeRoot = useMemo(() => buildFileTree(filesMap), [filesMap]);

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

  // Recursive tree node renderer
  const renderTreeNode = (node: FileTreeNode, depth = 0): React.ReactNode => {
    if (node.isFolder) {
      const isExpanded = expandedFolders[node.fullPath] !== false; // default expanded
      const childKeys = Object.keys(node.children).sort((a, b) => {
        const aIsFolder = node.children[a].isFolder;
        const bIsFolder = node.children[b].isFolder;
        if (aIsFolder && !bIsFolder) return -1;
        if (!aIsFolder && bIsFolder) return 1;
        return a.localeCompare(b);
      });

      return (
        <div key={node.fullPath || "root"} className="tree-folder-group">
          {node.fullPath && (
            <div
              className={`tree-item folder-item indent-${Math.min(depth, 5)}`}
              onClick={() => toggleFolder(node.fullPath)}
              title={`Folder: ${node.fullPath} (Click to toggle)`}
            >
              <div className="tree-item-left">
                {isExpanded ? (
                  <ChevronDown size={13} className="tree-chevron" />
                ) : (
                  <ChevronRight size={13} className="tree-chevron" />
                )}
                {isExpanded ? (
                  <FolderOpen size={14} className="folder-icon text-amber-700" />
                ) : (
                  <Folder size={14} className="folder-icon text-amber-700" />
                )}
                <span className="item-name font-medium">{node.name}</span>
              </div>
              <span className="folder-item-count">{childKeys.length}</span>
            </div>
          )}

          {(isExpanded || !node.fullPath) && (
            <div className="tree-folder-children">
              {childKeys.map((childKey) =>
                renderTreeNode(node.children[childKey], node.fullPath ? depth + 1 : depth)
              )}
            </div>
          )}
        </div>
      );
    }

    const file = node.file!;
    const isSelected = selectedFilePath === file.path;

    let badge = <FileText size={13} className="text-stone-500" />;
    const ext = file.name.split(".").pop()?.toLowerCase() || "";

    if (ext === "tsx" || ext === "ts") {
      badge = <span className="file-badge-text ts-icon font-mono font-bold">TS</span>;
    } else if (ext === "jsx" || ext === "js" || ext === "mjs") {
      badge = <span className="file-badge-text js-icon font-mono font-bold">JS</span>;
    } else if (ext === "py") {
      badge = <span className="file-badge-text py-icon font-mono font-bold">PY</span>;
    } else if (ext === "html") {
      badge = <span className="file-badge-text html-icon font-mono font-bold">5</span>;
    } else if (ext === "css") {
      badge = <span className="file-badge-text css-icon font-mono font-bold">#</span>;
    } else if (ext === "json") {
      badge = <span className="file-badge-text json-icon font-mono font-bold">{}</span>;
    } else if (ext === "md") {
      badge = <span className="file-badge-text md-icon font-mono font-bold">M↓</span>;
    } else if (ext === "svg" || ext === "png" || ext === "ico") {
      badge = <span className="file-badge-text img-icon font-mono font-bold">❖</span>;
    }

    return (
      <div
        key={file.path}
        className={`tree-item file-item indent-${Math.min(depth, 5)} ${
          isSelected ? "selected-file-pill" : ""
        }`}
        onClick={() => handleSelectFile(file)}
        title={`Click to preview code: ${file.path}`}
      >
        <div className="tree-item-left">
          {badge}
          <span className="item-name">{file.name}</span>
        </div>
        {isSelected && <span className="file-view-indicator">View</span>}
      </div>
    );
  };

  const displayRootName = openedFolderName || workspaceName || "workspace";

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
            {Object.keys(filesMap).length > 0 && (
              <span className="tab-badge files-count-badge">{Object.keys(filesMap).length}</span>
            )}
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
              <div className="feed-status-left">
                <span className="feed-title">NECTAR AGENT FEED</span>
                <span className="feed-count">{filteredMessages.length} updates</span>
              </div>

              <div className="feed-status-right">
                {onResetBoard && (
                  <button
                    type="button"
                    className="feed-status-action-btn"
                    onClick={() => {
                      onResetBoard();
                      showToast("Board & feed reset");
                    }}
                    title="Reset Feed & Whiteboard"
                  >
                    <span>↺</span>
                    <span>Reset</span>
                  </button>
                )}
                <button
                  type="button"
                  className={`feed-status-icon-btn ${showSearchInput ? "active" : ""}`}
                  onClick={() => setShowSearchInput((prev) => !prev)}
                  title="Search messages"
                >
                  <Search size={12} />
                </button>
              </div>
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
                  <p className="feed-empty-title">Ready for Your Goal</p>
                  <p className="feed-empty-sub">
                    Message Queen Bee below. Swarm agents will coordinate, research, code, and test automatically.
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

                      {/* Interactive MCQ Choice Chips if Queen provided options */}
                      {Array.isArray(m.metadata?.options) && (m.metadata.options as string[]).length > 0 && (
                        <div className="mcq-options-container" role="group" aria-label="Multiple choice options">
                          <span className="mcq-prompt-hint">Click a choice or type below:</span>
                          <div className="mcq-options-grid">
                            {(m.metadata.options as string[]).map((opt, oIdx) => {
                              const letter = String.fromCharCode(65 + oIdx);
                              return (
                                <button
                                  key={oIdx}
                                  type="button"
                                  className="mcq-option-chip"
                                  onClick={() => onSendMessage(opt)}
                                  title={`Choose: ${opt}`}
                                >
                                  <span className="mcq-letter-badge">{letter}</span>
                                  <span className="mcq-option-text">{opt}</span>
                                </button>
                              );
                            })}
                            <button
                              type="button"
                              className="mcq-option-chip mcq-custom-chip"
                              onClick={() => {
                                const inputEl = document.querySelector<HTMLInputElement>(".retro-feed-input");
                                if (inputEl) {
                                  inputEl.focus();
                                  inputEl.placeholder = "Type your own custom answer...";
                                }
                              }}
                              title="Type your own custom answer"
                            >
                              <span className="mcq-letter-badge">✏️</span>
                              <span className="mcq-option-text">Type your own answer...</span>
                            </button>
                          </div>
                        </div>
                      )}
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
                placeholder="Message Queen Bee to start swarm..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />

              {inputText.trim() && (
                <button
                  type="button"
                  className="input-clear-btn"
                  onClick={() => setInputText("")}
                  title="Clear input"
                >
                  <X size={13} />
                </button>
              )}

              <button
                type="submit"
                className="retro-feed-send-btn"
                title="Send instruction to Queen Bee"
                disabled={!inputText.trim()}
              >
                <Send size={14} />
              </button>
            </form>
          </div>
        ) : (
          /* PROJECT EXPLORER VIEW (Real-Time Working Directory Tree) */
          <div className="project-tree-view">
            {/* Live Working Directory Indicator Strip */}
            <div
              className="cwd-indicator-strip"
              title={`Live Working Directory: ${workspacePath || "Live Swarm Workspace"}`}
            >
              <div className="cwd-indicator-left">
                <span className="cwd-pulse-dot" />
                <span className="cwd-tag">CWD</span>
                <span className="cwd-path-text" title={workspacePath || "workspace/run-default"}>
                  {workspacePath
                    ? workspacePath.length > 30
                      ? `...${workspacePath.slice(-28)}`
                      : workspacePath
                    : "workspace/run-default"}
                </span>
              </div>
              <div className="cwd-indicator-right">
                <button
                  type="button"
                  className="cwd-icon-btn"
                  onClick={() => setShowOpenDirModal(true)}
                  title="Open different project directory / repo"
                >
                  <FolderOpen size={12} />
                </button>
                <button
                  type="button"
                  className="cwd-icon-btn"
                  onClick={() => {
                    if (workspacePath) {
                      navigator.clipboard.writeText(workspacePath);
                      showToast("Copied working directory path");
                    } else {
                      showToast("Live working directory connected");
                    }
                  }}
                  title="Copy Working Directory Path"
                >
                  <Copy size={11} />
                </button>
                <button
                  type="button"
                  className="cwd-icon-btn"
                  onClick={handleOpenInSystemExplorer}
                  title="Open Working Directory in File Explorer"
                >
                  <ExternalLink size={11} />
                </button>
              </div>
            </div>

            {/* Tree Root Header */}
            <div className="tree-root-header">
              <div
                className="tree-root-label"
                onClick={() => toggleFolder("__root__")}
                title={`Root: ${workspacePath || displayRootName} (Click to toggle)`}
              >
                {expandedFolders.__root__ !== false ? (
                  <ChevronDown size={14} className="tree-arrow" />
                ) : (
                  <ChevronRight size={14} className="tree-arrow" />
                )}
                <span className="tree-root-title">{displayRootName.toUpperCase()}</span>
                <span className="live-workspace-badge">LIVE CWD</span>
              </div>

              {/* Action Icons: Open Dir, New File, New Folder, Refresh */}
              <div className="tree-root-actions">
                <button
                  type="button"
                  className="tree-action-btn"
                  title="Open Directory / Project Folder"
                  onClick={() => setShowOpenDirModal(true)}
                >
                  <FolderUp size={13} />
                </button>

                <button
                  type="button"
                  className="tree-action-btn"
                  title="New File (relative to working directory)"
                  onClick={() => {
                    setIsCreatingFolder(false);
                    setIsCreatingFile(true);
                    setNewItemName("");
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
                  title="Refresh Working Directory (Real-time sync)"
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
                      <span>New File in {displayRootName}/</span>
                    </>
                  ) : (
                    <>
                      <Folder size={13} className="text-amber-800" />
                      <span>New Folder in {displayRootName}/</span>
                    </>
                  )}
                </div>
                <div className="inline-create-input-row">
                  <input
                    ref={newFileInputRef}
                    type="text"
                    className="inline-create-input"
                    placeholder={
                      isCreatingFile
                        ? "e.g. App.tsx, src/utils.ts, api/routes.py"
                        : "e.g. src/components, api/models"
                    }
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

            {/* Dynamic Hierarchical Tree Items from Live CWD */}
            {expandedFolders.__root__ !== false && (
              <div className="tree-items-list">
                {Object.keys(filesMap).length === 0 ? (
                  <div className="empty-tree-placeholder">
                    <HardDrive size={18} className="text-stone-400" />
                    <span>Working Directory is Empty</span>
                    <p>Ask Queen Bee to build a project, click '+' to create files, or click 'Open Directory'.</p>
                    <button
                      type="button"
                      className="open-dir-cta-btn"
                      onClick={() => setShowOpenDirModal(true)}
                    >
                      <FolderOpen size={13} />
                      <span>Open Project Directory</span>
                    </button>
                  </div>
                ) : (
                  renderTreeNode(treeRoot)
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Profile Bar */}
      <div className="sidebar-bottom-bar">
        <div className="sidebar-bottom-left-group">
          <div className="user-profile-pill">
            <div className="user-avatar-circle">
              <span role="img" aria-label="avatar">
                🧑‍💻
              </span>
            </div>
            <span className="user-profile-name">User1</span>
          </div>

          {/* Working Directory / Desktop Folder Popover Button */}
          <div className="sidebar-folder-btn-wrapper" ref={folderMenuRef}>
            <button
              type="button"
              className={`sidebar-folder-btn ${showFolderMenu ? "active" : ""}`}
              onClick={() => setShowFolderMenu((prev) => !prev)}
              title="Working Directory & Folder Actions"
              aria-label="Working Directory & Folder Actions"
            >
              <FolderOpen size={16} />
            </button>

            {/* Folder Actions Popover */}
            {showFolderMenu && (
              <div
                className="desktop-folder-popover"
                role="dialog"
                aria-label="Working directory menu"
              >
                <div className="popover-header">
                  <span className="popover-header-title">
                    <HardDrive size={13} />
                    <span>Working Directory & Files</span>
                  </span>
                  <button
                    type="button"
                    className="popover-close-btn"
                    onClick={() => setShowFolderMenu(false)}
                    title="Close"
                  >
                    <X size={13} />
                  </button>
                </div>

                {/* Active CWD Card */}
                <div className="popover-cwd-card">
                  <div className="cwd-card-header">
                    <span className="cwd-live-tag">
                      <span className="cwd-dot-green" /> LIVE RUNTIME CWD
                    </span>
                    <span className="cwd-file-count">{Object.keys(filesMap).length} files</span>
                  </div>
                  <div className="cwd-card-path" title={workspacePath || "./workspace/run-default"}>
                    <code>{workspacePath || "./workspace/run-default"}</code>
                  </div>
                </div>

                <div className="popover-options-list">
                  <button
                    type="button"
                    className="popover-option-btn primary-option"
                    onClick={() => {
                      setShowFolderMenu(false);
                      setShowOpenDirModal(true);
                    }}
                    title="Open any repository or project directory on this computer"
                  >
                    <div className="popover-option-icon">
                      <FolderOpen size={16} />
                    </div>
                    <div className="popover-option-text">
                      <span className="popover-option-label">Open Directory / Repo...</span>
                      <span className="popover-option-desc">
                        Switch live agent working directory to an existing project
                      </span>
                    </div>
                  </button>

                  <button
                    type="button"
                    className="popover-option-btn"
                    onClick={handleOpenInSystemExplorer}
                    title="Open Working Directory in Windows File Explorer"
                  >
                    <div className="popover-option-icon">
                      <ExternalLink size={16} />
                    </div>
                    <div className="popover-option-text">
                      <span className="popover-option-label">Open in File Explorer</span>
                      <span className="popover-option-desc">
                        Launch Windows Explorer at active working directory
                      </span>
                    </div>
                  </button>

                  <button
                    type="button"
                    className="popover-option-btn"
                    onClick={handleBrowseDesktopFolder}
                    title="Select an existing folder from your Desktop"
                  >
                    <div className="popover-option-icon">
                      <FolderUp size={16} />
                    </div>
                    <div className="popover-option-text">
                      <span className="popover-option-label">Browse from Desktop...</span>
                      <span className="popover-option-desc">
                        Use native browser folder picker
                      </span>
                    </div>
                  </button>

                  <button
                    type="button"
                    className="popover-option-btn"
                    onClick={() => {
                      handleOpenDirectoryPath("");
                      setShowFolderMenu(false);
                    }}
                    title="Reset back to standard sandbox workspace/run-default/"
                  >
                    <div className="popover-option-icon">
                      <RefreshCw size={16} />
                    </div>
                    <div className="popover-option-text">
                      <span className="popover-option-label">Reset to Sandbox Workspace</span>
                      <span className="popover-option-desc">
                        Switch back to isolated workspace/run-default/
                      </span>
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>
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

      {/* Hidden file/folder input for desktop folder picker */}
      <input
        type="file"
        ref={folderInputRef}
        {...({ webkitdirectory: "", directory: "" } as React.InputHTMLAttributes<HTMLInputElement>)}
        multiple
        style={{ display: "none" }}
        onChange={handleFolderInputSelected}
      />

      {/* Open Project Directory Modal */}
      {showOpenDirModal && (
        <div className="modal-backdrop" onClick={() => setShowOpenDirModal(false)}>
          <div
            className="open-dir-modal-card"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="open-dir-title"
          >
            <div className="open-dir-header">
              <div className="open-dir-header-left">
                <FolderOpen size={18} className="text-amber-800" />
                <div>
                  <h3 id="open-dir-title" className="open-dir-title">
                    Open Project Directory
                  </h3>
                  <span className="open-dir-subtitle">
                    Escape the sandbox: attach Swarm directly to any existing codebase (Gap 1)
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="retro-icon-btn"
                onClick={() => setShowOpenDirModal(false)}
                title="Close (Esc)"
              >
                <X size={16} />
              </button>
            </div>

            <div className="open-dir-body">
              <p className="open-dir-desc">
                Enter the absolute or relative path to your project. Queen Bee, Workers, and QA Bees will read, edit, and test directly inside this repository in real time.
              </p>

              <div className="open-dir-input-group">
                <label className="open-dir-label">Directory Path:</label>
                <div className="open-dir-input-wrapper">
                  <HardDrive size={15} className="input-dir-icon" />
                  <input
                    type="text"
                    className="styled-dir-input"
                    placeholder="e.g. C:\Users\tanma\Desktop\Projects\my-app or ./app"
                    value={targetDirPath}
                    onChange={(e) => setTargetDirPath(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && targetDirPath.trim()) {
                        handleOpenDirectoryPath(targetDirPath.trim());
                      }
                    }}
                    autoFocus
                  />
                  {targetDirPath && (
                    <button
                      type="button"
                      className="input-clear-btn"
                      onClick={() => setTargetDirPath("")}
                    >
                      <X size={13} />
                    </button>
                  )}
                </div>
              </div>

              {/* Preset Quick Chips */}
              <div className="dir-presets-section">
                <span className="presets-title">Quick Presets:</span>
                <div className="presets-chips-grid">
                  <button
                    type="button"
                    className="preset-chip-btn"
                    onClick={() => setTargetDirPath("./app")}
                    title="Switch to Swarm Frontend app/"
                  >
                    📁 Swarm Frontend (./app)
                  </button>
                  <button
                    type="button"
                    className="preset-chip-btn"
                    onClick={() => setTargetDirPath(".")}
                    title="Switch to repository root"
                  >
                    📁 Swarm Repo Root (.)
                  </button>
                  <button
                    type="button"
                    className="preset-chip-btn reset-chip"
                    onClick={() => setTargetDirPath("")}
                    title="Reset to sandboxed workspace/run-default"
                  >
                    🫙 Default Sandbox (run-default)
                  </button>
                </div>
              </div>

              <div className="open-dir-note">
                <span>🛡️ Path safety boundaries apply: secrets like <code>.env</code>, private keys, and <code>.git/</code> are strictly protected against modification.</span>
              </div>
            </div>

            <div className="open-dir-footer">
              <button
                type="button"
                className="retro-btn retro-btn-secondary"
                onClick={() => setShowOpenDirModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="retro-btn retro-btn-primary open-dir-submit-btn"
                onClick={() => handleOpenDirectoryPath(targetDirPath.trim())}
                disabled={isSwitchingDir}
              >
                {isSwitchingDir ? <RefreshCw size={14} className="spin-icon" /> : <FolderOpen size={14} />}
                <span>{targetDirPath.trim() ? "Open Directory" : "Reset to Sandbox"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
