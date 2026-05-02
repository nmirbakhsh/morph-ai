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

  return (
    <div className="stage">
      <motion.div
        className="world"
        animate={{ x: `${tx}vw`, y: `${ty}vh` }}
        transition={{ duration: 0.72, ease: [0.77, 0, 0.175, 1] }}
      >
        {list.map((n) => (
          <NodeCard
            key={n.node_id}
            node={n}
            isCurrent={n.coord_x === cx && n.coord_y === cy}
          />
        ))}
      </motion.div>
    </div>
  );
}
