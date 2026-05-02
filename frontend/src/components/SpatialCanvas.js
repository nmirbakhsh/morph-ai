import { jsx as _jsx } from "react/jsx-runtime";
import { motion } from "framer-motion";
import { useStore } from "../store";
import { NodeCard } from "./NodeCard";
export function SpatialCanvas() {
    const nodes = useStore((s) => s.nodesByCoord);
    const [cx, cy] = useStore((s) => s.currentCoord);
    const list = Object.values(nodes);
    // Translate world so the current coordinate sits at viewport origin (0,0).
    const tx = -cx * 100;
    const ty = -cy * 100;
    return (_jsx("div", { className: "stage", children: _jsx(motion.div, { className: "world", animate: { x: `${tx}vw`, y: `${ty}vh` }, transition: { duration: 0.72, ease: [0.77, 0, 0.175, 1] }, children: list.map((n) => (_jsx(NodeCard, { node: n, isCurrent: n.coord_x === cx && n.coord_y === cy }, n.node_id))) }) }));
}
