import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useStore } from "../store";
export function TopBar({ panelLabel }) {
    const chatOpen = useStore((s) => s.chatOpen);
    const toggleChat = useStore((s) => s.toggleChat);
    const toggleArchive = useStore((s) => s.toggleArchive);
    return (_jsxs("div", { className: "topbar", children: [_jsxs("div", { className: "logo-text", children: ["morph", _jsx("span", { children: "_ai" })] }), _jsx("div", { className: "panel-label", children: panelLabel }), _jsxs("div", { className: "topbar-right", children: [_jsx("button", { className: "pill-btn", onClick: toggleArchive, children: "Archive \u2197" }), _jsxs("button", { id: "chat-toggle", className: chatOpen ? "active" : "", onClick: toggleChat, children: [_jsx("span", { className: "chat-dot" }), "Ask Morph"] })] })] }));
}
