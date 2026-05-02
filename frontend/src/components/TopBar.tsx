import { useStore } from "../store";

export function TopBar({ panelLabel }: { panelLabel: string }) {
  const chatOpen = useStore((s) => s.chatOpen);
  const toggleChat = useStore((s) => s.toggleChat);
  const toggleArchive = useStore((s) => s.toggleArchive);

  return (
    <div className="topbar">
      <div className="logo-text">morph<span>_ai</span></div>
      <div className="panel-label">{panelLabel}</div>
      <div className="topbar-right">
        <button className="pill-btn" onClick={toggleArchive}>Archive ↗</button>
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
