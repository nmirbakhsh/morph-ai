import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
const NODE_W = 180;
const NODE_H = 110;
const SCALE = 80; // px per coord unit (zoomed out)
export function ArchiveMacroView() {
    const open = useStore((s) => s.archiveOpen);
    const toggle = useStore((s) => s.toggleArchive);
    const sessionId = useStore((s) => s.sessionId);
    const currentCoord = useStore((s) => s.currentCoord);
    const setCurrentCoord = useStore((s) => s.setCurrentCoord);
    const upsertNode = useStore((s) => s.upsertNode);
    const [nodes, setNodes] = useState([]);
    useEffect(() => {
        if (!open || !sessionId)
            return;
        api.graph(sessionId).then((g) => {
            setNodes(g.nodes);
            g.nodes.forEach(upsertNode);
        }).catch(() => { });
    }, [open, sessionId, upsertNode]);
    if (!open)
        return null;
    // Compute bounding box for centring.
    const xs = nodes.map((n) => n.coord_x);
    const ys = nodes.map((n) => n.coord_y);
    const minX = Math.min(0, ...xs), maxX = Math.max(0, ...xs);
    const minY = Math.min(0, ...ys), maxY = Math.max(0, ...ys);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const project = (x, y) => ({
        left: `calc(50% + ${(x - cx) * SCALE}px - ${NODE_W / 2}px)`,
        top: `calc(50% + ${(y - cy) * SCALE}px - ${NODE_H / 2}px)`,
    });
    // SVG for parent links
    const links = nodes
        .filter((n) => n.parent_node_id)
        .map((n) => {
        const parent = nodes.find((p) => p.node_id === n.parent_node_id);
        if (!parent)
            return null;
        const x1 = (parent.coord_x - cx) * SCALE;
        const y1 = (parent.coord_y - cy) * SCALE;
        const x2 = (n.coord_x - cx) * SCALE;
        const y2 = (n.coord_y - cy) * SCALE;
        return (_jsx("line", { x1: `calc(50% + ${x1}px)`, y1: `calc(50% + ${y1}px)`, x2: `calc(50% + ${x2}px)`, y2: `calc(50% + ${y2}px)`, stroke: "rgba(255,255,255,0.18)", strokeWidth: 1, strokeDasharray: "4 6" }, n.node_id));
    });
    return (_jsxs("div", { className: "archive-overlay", children: [_jsx("button", { className: "archive-close", onClick: toggle, children: "\u2715 Close archive" }), _jsxs("div", { className: "archive-canvas", children: [_jsx("svg", { style: { position: "absolute", inset: 0, width: "100%", height: "100%" }, children: links }), nodes.map((n) => {
                        const isCurrent = n.coord_x === currentCoord[0] && n.coord_y === currentCoord[1];
                        return (_jsxs("div", { className: `archive-node ${isCurrent ? "current" : ""}`, style: { ...project(n.coord_x, n.coord_y), width: NODE_W }, onClick: () => {
                                setCurrentCoord([n.coord_x, n.coord_y]);
                                toggle();
                            }, children: [_jsx("div", { className: "archive-node-eyebrow", children: n.layout.eyebrow }), _jsxs("div", { className: "archive-node-headline", children: [n.layout.icon, " ", n.title] })] }, n.node_id));
                    })] })] }));
}
