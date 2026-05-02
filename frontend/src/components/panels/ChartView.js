import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function ChartView({ block, accent }) {
    const series = block.series.length ? block.series : [10, 14, 12, 18, 22, 20, 26, 30, 28, 34];
    const min = Math.min(...series);
    const max = Math.max(...series);
    const range = max - min || 1;
    const w = 900;
    const h = 80;
    const stepX = w / Math.max(1, series.length - 1);
    const points = series
        .map((v, i) => `${i * stepX},${h - ((v - min) / range) * (h - 4) - 2}`)
        .join(" ");
    const areaPath = `M0,${h} L${points.replaceAll(" ", " L")} L${w},${h} Z`;
    const linePath = `M${points.replaceAll(" ", " L")}`;
    const gradId = `grad-${accent.replace("#", "")}`;
    return (_jsxs("div", { className: "chart-wrap", children: [_jsxs("div", { className: "chart-header", children: [_jsxs("div", { children: [_jsx("div", { className: "chart-title", children: block.title }), block.subtitle && _jsx("div", { className: "chart-sub", children: block.subtitle })] }), (block.hero_value || block.hero_delta) && (_jsxs("div", { style: { textAlign: "right" }, children: [block.hero_value && _jsx("div", { className: "chart-hero-val", children: block.hero_value }), block.hero_delta && (_jsx("div", { className: "chart-hero-delta", style: { color: accent }, children: block.hero_delta }))] }))] }), _jsxs("svg", { className: "sparkline", viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "none", children: [_jsx("defs", { children: _jsxs("linearGradient", { id: gradId, x1: "0", y1: "0", x2: "0", y2: "1", children: [_jsx("stop", { offset: "0%", stopColor: accent, stopOpacity: "0.35" }), _jsx("stop", { offset: "100%", stopColor: accent, stopOpacity: "0" })] }) }), _jsx("path", { d: areaPath, fill: `url(#${gradId})` }), _jsx("path", { d: linePath, fill: "none", stroke: accent, strokeWidth: 2.5, strokeLinejoin: "round" })] })] }));
}
