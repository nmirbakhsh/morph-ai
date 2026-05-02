import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function MetricBlockView({ block, accent }) {
    return (_jsxs("div", { className: "metric-block", children: [_jsx("div", { className: "metric-block-label", children: block.label }), _jsx("div", { className: "metric-block-value", style: { color: accent }, children: block.value }), block.sublabel && _jsx("div", { className: "metric-block-sub", children: block.sublabel })] }));
}
