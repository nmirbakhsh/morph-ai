import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function ListView({ block, accent }) {
    return (_jsxs("div", { className: "list-wrap", children: [block.title && _jsx("div", { className: "list-title", children: block.title }), block.items.map((it, i) => (_jsxs("div", { className: "list-item", children: [it.icon && _jsx("span", { className: "list-item-icon", children: it.icon }), _jsxs("div", { children: [_jsx("div", { className: "list-item-title", children: it.title }), it.subtitle && _jsx("div", { className: "list-item-sub", children: it.subtitle })] }), it.value && (_jsx("div", { className: "list-item-value", style: { color: accent }, children: it.value }))] }, i)))] }));
}
