import { useStore } from "../store";

export function TopBar({ panelLabel }: { panelLabel: string }) {
  const chatOpen = useStore((s) => s.chatOpen);
  const settingsOpen = useStore((s) => s.settingsOpen);
  const toggleChat = useStore((s) => s.toggleChat);
  const toggleSettings = useStore((s) => s.toggleSettings);

  return (
    <div className="topbar">
      <div className="logo-text">morph<span>_ai</span></div>
      <div className="panel-label">{panelLabel}</div>
      <div className="topbar-right">
        <button
          className={`pill-btn ${settingsOpen ? "active" : ""}`}
          onClick={toggleSettings}
          aria-label="Open settings"
          title="Settings"
        >
          ⚙ Settings
        </button>
        <button
          id="chat-toggle"
          className={chatOpen ? "active" : ""}
          onClick={toggleChat}
        >
          <span className="chat-dot" />
          Ask Morph
        </button>
      </div>
    </div>
  );
}
