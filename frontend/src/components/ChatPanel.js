import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
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
    const [messages, setMessages] = useState([
        { role: "ai", html: "Hi! Ask me to take you anywhere. Try <em>“take me to a room about ancient Rome”</em>." },
    ]);
    const [chips, setChips] = useState(DEFAULT_CHIPS);
    const [input, setInput] = useState("");
    const [busy, setBusy] = useState(false);
    const scrollRef = useRef(null);
    useEffect(() => {
        if (scrollRef.current)
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages.length]);
    const send = async (text) => {
        if (!sessionId || !currentNode || busy)
            return;
        if (!text.trim())
            return;
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
            if (resp.followups?.length)
                setChips(resp.followups);
            if (resp.teleport_node) {
                upsertNode(resp.teleport_node);
                setCurrentCoord([resp.teleport_node.coord_x, resp.teleport_node.coord_y]);
            }
        }
        catch (e) {
            setMessages((m) => {
                const trimmed = m.slice(0, -1);
                return [...trimmed, { role: "ai", html: "Sorry — I couldn’t reach the model." }];
            });
        }
        finally {
            setBusy(false);
        }
    };
    if (!open)
        return null;
    return (_jsxs("div", { className: "chat-panel", role: "dialog", "aria-label": "Morph AI chat", children: [_jsxs("div", { className: "chat-header", children: [_jsx("div", { className: "chat-header-icon", children: "\u2726" }), _jsxs("div", { children: [_jsx("div", { className: "chat-header-title", children: "Morph AI" }), _jsx("div", { className: "chat-header-sub", children: "Type to teleport anywhere" })] }), _jsx("button", { className: "chat-header-close", onClick: toggle, "aria-label": "Close chat", children: "\u2715" })] }), _jsxs("div", { className: "chat-messages", ref: scrollRef, children: [messages.map((m, i) => (_jsx("div", { className: `msg ${m.role}`, children: _jsx("div", { className: "msg-bubble", dangerouslySetInnerHTML: { __html: m.html } }) }, i))), busy && (_jsx("div", { className: "msg ai", children: _jsx("div", { className: "msg-bubble", children: _jsxs("div", { className: "typing-dots", children: [_jsx("span", {}), _jsx("span", {}), _jsx("span", {})] }) }) }))] }), _jsx("div", { className: "chat-suggestions", children: chips.map((c, i) => (_jsx("span", { className: "chip", onClick: () => send(c), children: c }, i))) }), _jsxs("div", { className: "chat-input-row", children: [_jsx("textarea", { className: "chat-input", placeholder: "Ask anything\u2026", rows: 1, value: input, onChange: (e) => setInput(e.target.value), onKeyDown: (e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                send(input);
                            }
                        } }), _jsx("button", { className: "chat-send", disabled: busy || !input.trim(), onClick: () => send(input), "aria-label": "Send", children: "\u2191" })] })] }));
}
function escape(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
