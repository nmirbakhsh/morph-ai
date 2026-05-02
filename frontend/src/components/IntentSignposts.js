import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
const ARROWS = {
    up: "↑", down: "↓", left: "←", right: "→",
};
export function IntentSignposts({ intents, onPick }) {
    return (_jsx(_Fragment, { children: intents.map((it) => (_jsxs("div", { className: [
                "signpost", it.direction,
                it.is_back ? "is-back" : "",
                it.is_continuation ? "is-continuation" : "",
            ].filter(Boolean).join(" "), onClick: () => onPick(it), role: "button", tabIndex: 0, children: [(it.direction === "up" || it.direction === "left") && (_jsx("div", { className: "signpost-arrow", children: ARROWS[it.direction] })), _jsx("div", { className: "signpost-icon", children: it.icon }), _jsx("div", { className: "signpost-label", children: it.label }), _jsx("div", { className: "signpost-sub", children: it.sublabel }), (it.direction === "down" || it.direction === "right") && (_jsx("div", { className: "signpost-arrow", children: ARROWS[it.direction] }))] }, it.direction))) }));
}
