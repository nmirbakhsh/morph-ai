import { useEffect, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import type { NodeRecord } from "../types";

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

  const [nodes, setNodes] = useState<NodeRecord[]>([]);

  useEffect(() => {
    if (!open || !sessionId) return;
    api.graph(sessionId).then((g) => {
      setNodes(g.nodes);
      g.nodes.forEach(upsertNode);
    }).catch(() => {});
  }, [open, sessionId, upsertNode]);

  if (!open) return null;

  // Compute bounding box for centring.
  const xs = nodes.map((n) => n.coord_x);
  const ys = nodes.map((n) => n.coord_y);
  const minX = Math.min(0, ...xs), maxX = Math.max(0, ...xs);
  const minY = Math.min(0, ...ys), maxY = Math.max(0, ...ys);
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  const project = (x: number, y: number) => ({
    left: `calc(50% + ${(x - cx) * SCALE}px - ${NODE_W / 2}px)`,
    top: `calc(50% + ${(y - cy) * SCALE}px - ${NODE_H / 2}px)`,
  });

  // SVG for parent links
  const links = nodes
    .filter((n) => n.parent_node_id)
    .map((n) => {
      const parent = nodes.find((p) => p.node_id === n.parent_node_id);
      if (!parent) return null;
      const x1 = (parent.coord_x - cx) * SCALE;
      const y1 = (parent.coord_y - cy) * SCALE;
      const x2 = (n.coord_x - cx) * SCALE;
      const y2 = (n.coord_y - cy) * SCALE;
      return (
        <line
          key={n.node_id}
          x1={`calc(50% + ${x1}px)`}
          y1={`calc(50% + ${y1}px)`}
          x2={`calc(50% + ${x2}px)`}
          y2={`calc(50% + ${y2}px)`}
          stroke="rgba(255,255,255,0.18)"
          strokeWidth={1}
          strokeDasharray="4 6"
        />
      );
    });

  return (
    <div className="archive-overlay">
      <button className="archive-close" onClick={toggle}>✕ Close archive</button>
      <div className="archive-canvas">
        <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
          {links}
        </svg>
        {nodes.map((n) => {
          const isCurrent = n.coord_x === currentCoord[0] && n.coord_y === currentCoord[1];
          return (
            <div
              key={n.node_id}
              className={`archive-node ${isCurrent ? "current" : ""}`}
              style={{ ...project(n.coord_x, n.coord_y), width: NODE_W }}
              onClick={() => {
                setCurrentCoord([n.coord_x, n.coord_y]);
                toggle();
              }}
            >
              <div className="archive-node-eyebrow">{n.layout.eyebrow}</div>
              <div className="archive-node-headline">
                {n.layout.icon} {n.title}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
