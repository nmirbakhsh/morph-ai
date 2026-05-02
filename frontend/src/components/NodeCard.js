import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { motion } from "framer-motion";
import { ChartView } from "./panels/ChartView";
import { ListView } from "./panels/ListView";
import { MetricBlockView } from "./panels/MetricBlockView";
import { StatGridView } from "./panels/StatGridView";
import { TagRowView } from "./panels/TagRowView";
import { TextBlockView } from "./panels/TextBlockView";
export function NodeCard({ node, isCurrent }) {
    const { layout } = node;
    const accent = layout.accent_color || "#a78bfa";
    return (_jsx("div", { className: `panel theme-${layout.theme || "violet"}`, style: {
            left: `${node.coord_x * 100}vw`,
            top: `${node.coord_y * 100}vh`,
        }, "data-node-id": node.node_id, children: _jsx("div", { className: "panel-scroll", children: _jsxs(motion.div, { className: "panel-inner", initial: { opacity: 0, y: 16 }, animate: { opacity: isCurrent ? 1 : 0.85, y: 0 }, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] }, children: [_jsx("div", { className: "panel-icon", children: layout.icon }), _jsx("div", { className: "eyebrow", children: layout.eyebrow }), _jsxs("h1", { className: "headline", children: [layout.headline, layout.headline_accent && (_jsxs(_Fragment, { children: [_jsx("br", {}), _jsx("em", { style: { color: accent }, children: layout.headline_accent })] }))] }), layout.body && _jsx("p", { className: "body-lg", style: { marginTop: 18 }, children: layout.body }), layout.components.map((c, i) => {
                        switch (c.type) {
                            case "stat_grid": return _jsx(StatGridView, { block: c }, i);
                            case "chart": return _jsx(ChartView, { block: c, accent: accent }, i);
                            case "list": return _jsx(ListView, { block: c, accent: accent }, i);
                            case "text_block": return _jsx(TextBlockView, { block: c }, i);
                            case "metric_block": return _jsx(MetricBlockView, { block: c, accent: accent }, i);
                            case "tag_row": return _jsx(TagRowView, { block: c }, i);
                            default: return null;
                        }
                    })] }) }) }));
}
