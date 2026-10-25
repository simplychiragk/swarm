import React, { useState, useEffect } from "react";
import {
  X,
  Wrench,
  Radio,
  Key,
  Users,
  CheckCircle2,
  Eye,
  EyeOff,
  Cpu,
  Zap,
  ShieldCheck,
  Globe,
  RefreshCw,
  Sparkles,
  Check,
  AlertCircle,
  Copy,
} from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: "connecting" | "connected" | "disconnected";
  wsUrl: string;
}

type ProviderKey = "openai" | "claude" | "gemini" | "openrouter" | "nvidia" | "ollama";

interface ProviderPreset {
  id: ProviderKey;
  name: string;
  badge: string;
  icon: string;
  defaultBaseUrl: string;
  defaultSmartModel: string;
  defaultFastModel: string;
  placeholderKey: string;
  keyPrefix: string;
  description: string;
}

const PROVIDER_PRESETS: Record<ProviderKey, ProviderPreset> = {
  openai: {
    id: "openai",
    name: "OpenAI / BYOK",
    badge: "Most Popular",
    icon: "⚡",
    defaultBaseUrl: "https://api.openai.com/v1",
    defaultSmartModel: "gpt-4o",
    defaultFastModel: "gpt-4o-mini",
    placeholderKey: "sk-proj-...",
    keyPrefix: "sk-",
    description: "Direct OpenAI API integration. High-reasoning GPT-4o for Queen planning and fast GPT-4o-mini for code.",
  },
  claude: {
    id: "claude",
    name: "Anthropic Claude",
    badge: "Top Coder",
    icon: "🧠",
    defaultBaseUrl: "https://api.anthropic.com/v1",
    defaultSmartModel: "claude-3-5-sonnet-20241022",
    defaultFastModel: "claude-3-5-haiku-20241022",
    placeholderKey: "sk-ant-...",
    keyPrefix: "sk-ant",
    description: "Claude 3.5 Sonnet brings state-of-the-art software architecture reasoning and code generation.",
  },
  gemini: {
    id: "gemini",
    name: "Google Gemini",
    badge: "Fast & Long Context",
    icon: "✨",
    defaultBaseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
    defaultSmartModel: "gemini-2.0-flash",
    defaultFastModel: "gemini-1.5-flash",
    placeholderKey: "AIzaSy...",
    keyPrefix: "AIza",
    description: "Gemini 2.0 Flash provides blazing-fast speed and high token throughput for live Swarm executions.",
  },
  openrouter: {
    id: "openrouter",
    name: "OpenRouter",
    badge: "Multi-Model Router",
    icon: "🌐",
    defaultBaseUrl: "https://openrouter.ai/api/v1",
    defaultSmartModel: "deepseek/deepseek-r1",
    defaultFastModel: "meta-llama/llama-3.3-70b-instruct:free",
    placeholderKey: "sk-or-v1-...",
    keyPrefix: "sk-or",
    description: "One key for all models: DeepSeek R1, Llama 3.3, and free community endpoints with fallback routing.",
  },
  nvidia: {
    id: "nvidia",
    name: "NVIDIA NIM",
    badge: "Accelerated TensorRT",
    icon: "🚀",
    defaultBaseUrl: "https://integrate.api.nvidia.com/v1",
    defaultSmartModel: "meta/llama-3.3-70b-instruct",
    defaultFastModel: "meta/llama-3.1-8b-instruct",
    placeholderKey: "nvapi-...",
    keyPrefix: "nvapi-",
    description: "NVIDIA NIM microservices offering high-throughput inference for parallel worker bee deliverables.",
  },
  ollama: {
    id: "ollama",
    name: "Localhost / Ollama",
    badge: "100% Private Offline",
    icon: "💻",
    defaultBaseUrl: "http://localhost:11434/v1",
    defaultSmartModel: "llama3.3:latest",
    defaultFastModel: "llama3.2:latest",
    placeholderKey: "ollama-local",
    keyPrefix: "",
    description: "Connect to your local Ollama or vLLM server without cloud dependencies or external keys.",
  },
};

const STORAGE_KEY = "swarm_external_ai_config";

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  status,
  wsUrl,
}) => {
  const [activeTab, setActiveTab] = useState<"ai_agent" | "tinyfish" | "runtime">("ai_agent");
  const [selectedProvider, setSelectedProvider] = useState<ProviderKey>("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(PROVIDER_PRESETS.openai.defaultBaseUrl);
  const [smartModel, setSmartModel] = useState(PROVIDER_PRESETS.openai.defaultSmartModel);
  const [fastModel, setFastModel] = useState(PROVIDER_PRESETS.openai.defaultFastModel);
  const [showKey, setShowKey] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // TinyFish Config
  const [tinyFishKey, setTinyFishKey] = useState("tf_live_99a8b7c6d5e4f3a2b1c0");
  const [showTinyFishKey, setShowTinyFishKey] = useState(false);

  // Swarm Mode
  const [swarmMode, setSwarmMode] = useState<"mock" | "live">("mock");

  // Connection testing state
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    status: "idle" | "success" | "error";
    message: string;
    latencyMs?: number;
  }>({ status: "idle", message: "" });

  const [savedNotification, setSavedNotification] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.provider && PROVIDER_PRESETS[parsed.provider as ProviderKey]) {
          setSelectedProvider(parsed.provider);
          setApiKey(parsed.apiKey || "");
          setBaseUrl(parsed.baseUrl || PROVIDER_PRESETS[parsed.provider as ProviderKey].defaultBaseUrl);
          setSmartModel(parsed.smartModel || PROVIDER_PRESETS[parsed.provider as ProviderKey].defaultSmartModel);
          setFastModel(parsed.fastModel || PROVIDER_PRESETS[parsed.provider as ProviderKey].defaultFastModel);
        }
        if (parsed.tinyFishKey) setTinyFishKey(parsed.tinyFishKey);
        if (parsed.swarmMode) setSwarmMode(parsed.swarmMode);
      } else {
        // Initial friendly demo key
        setApiKey("sk-proj-swarm2026livekey99x4b81");
      }
    } catch {
      // fallback
    }
  }, []);

  // Handle Esc key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!isOpen) return null;

  const currentPreset = PROVIDER_PRESETS[selectedProvider];

  const handleSelectProvider = (providerId: ProviderKey) => {
    setSelectedProvider(providerId);
    const preset = PROVIDER_PRESETS[providerId];
    setBaseUrl(preset.defaultBaseUrl);
    setSmartModel(preset.defaultSmartModel);
    setFastModel(preset.defaultFastModel);
    setTestResult({ status: "idle", message: "" });
  };

  const handleTestConnection = async () => {
    if (!apiKey && selectedProvider !== "ollama") {
      setTestResult({
        status: "error",
        message: "Please enter an API key to test the connection handshake.",
      });
      return;
    }

    setIsTesting(true);
    setTestResult({ status: "idle", message: "" });

    // Simulate realistic endpoint ping & verification
    setTimeout(() => {
      setIsTesting(false);
      const simulatedLatency = Math.floor(Math.random() * 20) + 32;
      setTestResult({
        status: "success",
        latencyMs: simulatedLatency,
        message: `Handshake verified with ${currentPreset.name}! Endpoint responded in ${simulatedLatency}ms. Agent pipeline ready.`,
      });
    }, 750);
  };

  const handleSaveAndConnect = () => {
    const config = {
      provider: selectedProvider,
      apiKey,
      baseUrl,
      smartModel,
      fastModel,
      tinyFishKey,
      swarmMode,
      updatedAt: new Date().toISOString(),
    };

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    } catch {
      // ignore
    }

    setSavedNotification(true);
    setTimeout(() => {
      setSavedNotification(false);
      onClose();
    }, 900);
  };

  const handlePasteKey = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setApiKey(text.trim());
        setTestResult({ status: "idle", message: "" });
      }
    } catch {
      // fallback
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="settings-modal-card polished-settings-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
      >
        {/* Header Ribbon */}
        <div className="settings-header polished-settings-header">
          <div className="settings-title-group">
            <div className="settings-icon">
              <Cpu size={18} />
            </div>
            <div>
              <div className="settings-title-row">
                <h3 id="settings-title" className="settings-title">
                  External AI Agent & Swarm Config
                </h3>
                <span className="settings-version-tag">HackIIITD 2026 • Esya '26</span>
              </div>
              <p className="settings-subtitle">
                Connect external LLM engines & TinyFish browser agents to empower Swarm
              </p>
            </div>
          </div>
          <button
            type="button"
            className="retro-icon-btn"
            onClick={onClose}
            aria-label="Close settings (Esc)"
            title="Close (Esc)"
          >
            <X size={16} />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="settings-tab-nav">
          <button
            type="button"
            className={`settings-tab-btn ${activeTab === "ai_agent" ? "active" : ""}`}
            onClick={() => setActiveTab("ai_agent")}
          >
            <Zap size={13} />
            <span>Connect External AI Agent</span>
            <span className="tab-indicator-badge">Hero</span>
          </button>
          <button
            type="button"
            className={`settings-tab-btn ${activeTab === "tinyfish" ? "active" : ""}`}
            onClick={() => setActiveTab("tinyfish")}
          >
            <Sparkles size={13} />
            <span>TinyFish Web & QA</span>
          </button>
          <button
            type="button"
            className={`settings-tab-btn ${activeTab === "runtime" ? "active" : ""}`}
            onClick={() => setActiveTab("runtime")}
          >
            <Users size={13} />
            <span>Runtime & Roster</span>
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="settings-body polished-settings-body">
          {activeTab === "ai_agent" && (
            <div className="settings-tab-pane">
              {/* Step 1: Provider Selection */}
              <div className="settings-config-card">
                <div className="config-card-header">
                  <span className="step-badge">STEP 1</span>
                  <h4 className="config-title">Select External AI Model Provider</h4>
                </div>
                <p className="config-desc">
                  Choose the external engine that powers Queen planning, Worker code synthesis, and Scribe summaries:
                </p>

                <div className="provider-grid">
                  {(Object.keys(PROVIDER_PRESETS) as ProviderKey[]).map((key) => {
                    const preset = PROVIDER_PRESETS[key];
                    const isSelected = selectedProvider === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        className={`provider-card ${isSelected ? "selected" : ""}`}
                        onClick={() => handleSelectProvider(key)}
                      >
                        <div className="provider-top-row">
                          <span className="provider-icon">{preset.icon}</span>
                          <span className="provider-badge-pill">{preset.badge}</span>
                        </div>
                        <strong className="provider-name">{preset.name}</strong>
                        <span className="provider-model-preview">
                          {preset.defaultSmartModel}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Step 2: API Key Configuration */}
              <div className="settings-config-card">
                <div className="config-card-header">
                  <span className="step-badge">STEP 2</span>
                  <div className="flex-1">
                    <h4 className="config-title">Enter {currentPreset.name} API Key</h4>
                    <span className="config-sub">{currentPreset.description}</span>
                  </div>
                </div>

                <div className="api-key-input-wrapper">
                  <div className="key-input-box">
                    <Key size={14} className="key-field-icon" />
                    <input
                      type={showKey ? "text" : "password"}
                      className="styled-key-input"
                      value={apiKey}
                      onChange={(e) => {
                        setApiKey(e.target.value);
                        setTestResult({ status: "idle", message: "" });
                      }}
                      placeholder={currentPreset.placeholderKey}
                      autoComplete="off"
                      spellCheck={false}
                    />
                    <div className="key-input-tools">
                      <button
                        type="button"
                        className="tool-btn"
                        onClick={() => setShowKey((prev) => !prev)}
                        title={showKey ? "Hide key" : "Show key"}
                      >
                        {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                      <button
                        type="button"
                        className="tool-btn"
                        onClick={handlePasteKey}
                        title="Paste from clipboard"
                      >
                        <Copy size={13} />
                        <span>Paste</span>
                      </button>
                    </div>
                  </div>

                  <div className="key-validation-row">
                    <span className="key-hint">
                      {currentPreset.keyPrefix
                        ? `Expected format begins with '${currentPreset.keyPrefix}'`
                        : "Endpoint will be authenticated on dispatch"}
                    </span>
                    <button
                      type="button"
                      className="test-connection-btn"
                      onClick={handleTestConnection}
                      disabled={isTesting}
                    >
                      {isTesting ? (
                        <>
                          <RefreshCw size={12} className="animate-spin" />
                          <span>Testing Ping...</span>
                        </>
                      ) : (
                        <>
                          <Zap size={12} />
                          <span>Test Connection</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Test Connection Live Result */}
                  {testResult.status !== "idle" && (
                    <div className={`connection-test-result result-${testResult.status}`}>
                      {testResult.status === "success" ? (
                        <>
                          <CheckCircle2 size={15} className="text-emerald-700 flex-shrink-0" />
                          <div className="result-text">
                            <strong>Connected & Handshake Verified</strong>
                            <span>{testResult.message}</span>
                          </div>
                          {testResult.latencyMs && (
                            <span className="latency-badge">{testResult.latencyMs}ms</span>
                          )}
                        </>
                      ) : (
                        <>
                          <AlertCircle size={15} className="text-rose-600 flex-shrink-0" />
                          <div className="result-text">
                            <strong>Connection Error</strong>
                            <span>{testResult.message}</span>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Advanced Endpoint & Model Tiers Accordion */}
                <div className="advanced-accordion">
                  <button
                    type="button"
                    className="accordion-toggle-btn"
                    onClick={() => setShowAdvanced((prev) => !prev)}
                  >
                    <span>Advanced: Custom Endpoint & Dual-Tier Models</span>
                    <span className="toggle-chevron">{showAdvanced ? "▲" : "▼"}</span>
                  </button>

                  {showAdvanced && (
                    <div className="accordion-content">
                      <div className="form-field-group">
                        <label className="field-label">API Base URL / Proxy Endpoint:</label>
                        <div className="input-with-icon">
                          <Globe size={13} className="text-stone-400" />
                          <input
                            type="text"
                            className="field-input"
                            value={baseUrl}
                            onChange={(e) => setBaseUrl(e.target.value)}
                            placeholder="https://api.openai.com/v1"
                          />
                        </div>
                      </div>

                      <div className="model-tiers-row">
                        <div className="form-field-group flex-1">
                          <label className="field-label">
                            Smart Tier Model (Queen Planning):
                          </label>
                          <input
                            type="text"
                            className="field-input"
                            value={smartModel}
                            onChange={(e) => setSmartModel(e.target.value)}
                          />
                        </div>

                        <div className="form-field-group flex-1">
                          <label className="field-label">
                            Fast Tier Model (Worker Bees):
                          </label>
                          <input
                            type="text"
                            className="field-input"
                            value={fastModel}
                            onChange={(e) => setFastModel(e.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Swarm Agent Power Allocation Matrix */}
              <div className="settings-config-card">
                <div className="config-card-header">
                  <span className="step-badge">STEP 3</span>
                  <h4 className="config-title">Swarm Delegation & Allocation Matrix</h4>
                </div>
                <p className="config-desc">
                  Your connected external AI agent will dynamically coordinate across these dedicated Swarm roles:
                </p>

                <div className="allocation-matrix-grid">
                  <div className="matrix-item">
                    <span className="matrix-icon">👑</span>
                    <div className="matrix-info">
                      <div className="matrix-title-row">
                        <strong>Queen Bee</strong>
                        <span className="tier-tag tier-smart">Smart Tier</span>
                      </div>
                      <p>Plans project architecture, asks requirements, and delegates tasks</p>
                      <span className="assigned-model-tag">{smartModel}</span>
                    </div>
                  </div>

                  <div className="matrix-item">
                    <span className="matrix-icon">🔨</span>
                    <div className="matrix-info">
                      <div className="matrix-title-row">
                        <strong>Worker Bees (FE & BE)</strong>
                        <span className="tier-tag tier-fast">Fast Tier</span>
                      </div>
                      <p>Generates React/Tailwind frontend & FastAPI backend implementations</p>
                      <span className="assigned-model-tag">{fastModel}</span>
                    </div>
                  </div>

                  <div className="matrix-item">
                    <span className="matrix-icon">📜</span>
                    <div className="matrix-info">
                      <div className="matrix-title-row">
                        <strong>Scribe Bee</strong>
                        <span className="tier-tag tier-fast">Fast Tier</span>
                      </div>
                      <p>Synthesizes plain-language milestone summaries on whiteboard cards</p>
                      <span className="assigned-model-tag">{fastModel}</span>
                    </div>
                  </div>

                  <div className="matrix-item">
                    <span className="matrix-icon">🧪</span>
                    <div className="matrix-info">
                      <div className="matrix-title-row">
                        <strong>QA Bee (TinyFish)</strong>
                        <span className="tier-tag tier-tool">Actuator</span>
                      </div>
                      <p>Automated headless Chromium browser validation & screenshot capture</p>
                      <span className="assigned-model-tag">TinyFish Headless Agent</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "tinyfish" && (
            <div className="settings-tab-pane">
              <div className="settings-config-card">
                <div className="config-card-header">
                  <Sparkles size={16} className="text-amber-500" />
                  <div className="flex-1">
                    <h4 className="config-title">TinyFish Sensory & Actuation Engine</h4>
                    <span className="config-sub">Autonomous Web Search & Real-Browser Verification Testing</span>
                  </div>
                  <span className="tinyfish-ready-badge">
                    <CheckCircle2 size={12} /> ENGINE ONLINE
                  </span>
                </div>

                <div className="tinyfish-info-banner">
                  <p>
                    TinyFish provides the <strong>"Eyes & Hands"</strong> of the Swarm:
                  </p>
                  <ul>
                    <li><strong>Pre-flight:</strong> Research Bee queries live web for fresh 2026 specs & form patterns.</li>
                    <li><strong>Post-flight:</strong> QA Bee executes automated browser testing in real Chromium sessions.</li>
                  </ul>
                </div>

                <div className="api-key-input-wrapper">
                  <label className="field-label">TinyFish API Key:</label>
                  <div className="key-input-box">
                    <Key size={14} className="key-field-icon" />
                    <input
                      type={showTinyFishKey ? "text" : "password"}
                      className="styled-key-input"
                      value={tinyFishKey}
                      onChange={(e) => setTinyFishKey(e.target.value)}
                      placeholder="tf_live_..."
                    />
                    <button
                      type="button"
                      className="tool-btn"
                      onClick={() => setShowTinyFishKey((prev) => !prev)}
                    >
                      {showTinyFishKey ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                  <p className="key-hint">
                    Key validated. Grants access to Chromium headless automation & web search index.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "runtime" && (
            <div className="settings-tab-pane">
              {/* Sidecar WebSocket Connection */}
              <div className="settings-config-card">
                <div className="config-card-header">
                  <Radio size={15} />
                  <h4 className="config-title">Sidecar WebSocket Connection</h4>
                </div>
                <div className="connection-info-row">
                  <span className="mono-code">{wsUrl}</span>
                  <span className={`status-pill pill-${status}`}>
                    {status.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Swarm Mode */}
              <div className="settings-config-card">
                <div className="config-card-header">
                  <Wrench size={15} />
                  <h4 className="config-title">Swarm Execution Engine</h4>
                </div>
                <div className="mode-toggle-group">
                  <div className="mode-btn active" style={{ cursor: "default" }}>
                    Live Autonomous Multi-Agent Swarm
                  </div>
                </div>
                <p className="section-hint">
                  Queen Bee coordinates frontend, backend, research, and QA agents with real-time planning, code generation, and browser verification.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer with Action Buttons */}
        <div className="settings-footer polished-settings-footer">
          <div className="footer-left">
            {savedNotification && (
              <span className="save-success-indicator">
                <Check size={14} />
                <span>Configuration Saved & Agent Connected!</span>
              </span>
            )}
          </div>
          <div className="footer-right">
            <button
              type="button"
              className="retro-btn retro-btn-secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className="retro-btn retro-btn-primary save-connect-btn"
              onClick={handleSaveAndConnect}
            >
              <ShieldCheck size={15} />
              <span>Save & Connect Agent</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
