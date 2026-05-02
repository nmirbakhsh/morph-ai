import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function StatGridView({ block }) {
    return (_jsx("div", { className: "stat-grid", children: block.items.map((it, i) => (_jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-label", children: it.label }), _jsx("div", { className: "stat-value", children: it.value }), it.delta && (_jsxs("div", { className: `stat-delta ${it.trend ?? "flat"}`, children: [it.trend === "up" ? "↑ " : it.trend === "down" ? "↓ " : "· ", it.delta] }))] }, i))) }));
}
