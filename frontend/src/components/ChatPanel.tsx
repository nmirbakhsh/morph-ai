import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";

interface ChatMsg { role: "user" | "ai"; html: string; }

const DEFAULT_CHIPS = [
  "Show me something curious about Mars",
  "Tell me about the Eiffel Tower",
  "Take me somewhere unexpected",
  "Search for ‘quantum entanglement’",
];

export function ChatPanel() {
  const open = useStore((s) => s.chatOpen);
  const toggle = useStore((s) => s.toggleChat);
  const sessionId = useStore((s) => s.sessionId);
  const currentCoord = useStore((s) => s.currentCoord);
  const nodesByCoord = useStore((s) => s.nodesByCoord);
  const upsertNode = useStore((s) => s.upsertNode);
  const setCurrentCoord = useStore((s) => s.setCurrentCoord);

  const currentNode = nodesByCoord[`${currentCoord[0]},${currentCoord[1]}`];

  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: "ai", html: "Hi! Ask me to take you anywhere. Try <em>“take me to a room about ancient Rome”</em>." },
  ]);
  const [chips, setChips] = useState<string[]>(DEFAULT_CHIPS);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length]);

  const send = async (text: string) => {
    if (!sessionId || !currentNode || busy) return;
    if (!text.trim()) return;
    setMessages((m) => [...m, { role: "user", html: escape(text) }, { role: "ai", html: "…thinking…" }]);
    setInput("");
    setBusy(true);
    try {
      const resp = await api.chat({
        session_id: sessionId,
        current_node_id: currentNode.node_id,
        message: text,
      });
      setMessages((m) => {
        const trimmed = m.slice(0, -1); // drop the placeholder
        return [...trimmed, { role: "ai", html: escape(resp.reply) }];
      });
      if (resp.followups?.length) setChips(resp.followups);
      if (resp.teleport_node) {
        upsertNode(resp.teleport_node);
        setCurrentCoord([resp.teleport_node.coord_x, resp.teleport_node.coord_y]);
      }
    } catch (e) {
      setMessages((m) => {
        const trimmed = m.slice(0, -1);
        return [...trimmed, { role: "ai", html: "Sorry — I couldn’t reach the model." }];
      });
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;
  return (
    <div className="chat-panel" role="dialog" aria-label="Morph AI chat">
      <div className="chat-header">
        <div className="chat-header-icon">✦</div>
        <div>
          <div className="chat-header-title">Morph AI</div>
          <div className="chat-header-sub">Type to teleport anywhere</div>
        </div>
        <button className="chat-header-close" onClick={toggle} aria-label="Close chat">✕</button>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <div className={`msg ${m.role}`} key={i}>
            <div className="msg-bubble" dangerouslySetInnerHTML={{ __html: m.html }} />
          </div>
        ))}
        {busy && (
          <div className="msg ai">
            <div className="msg-bubble">
              <div className="typing-dots"><span /><span /><span /></div>
            </div>
          </div>
        )}
      </div>

      <div className="chat-suggestions">
        {chips.map((c, i) => (
          <span className="chip" key={i} onClick={() => send(c)}>{c}</span>
        ))}
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          placeholder="Ask anything…"
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
        />
        <button
          className="chat-send"
          disabled={busy || !input.trim()}
          onClick={() => send(input)}
          aria-label="Send"
        >
          ↑
        </button>
      </div>
    </div>
  );
}

function escape(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
