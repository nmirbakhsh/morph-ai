import { motion } from "framer-motion";
import type { NodeRecord } from "../types";
import { ChartView } from "./panels/ChartView";
import { ListView } from "./panels/ListView";
import { MetricBlockView } from "./panels/MetricBlockView";
import { StatGridView } from "./panels/StatGridView";
import { TagRowView } from "./panels/TagRowView";
import { TextBlockView } from "./panels/TextBlockView";

interface Props {
  node: NodeRecord;
  isCurrent: boolean;
}

export function NodeCard({ node, isCurrent }: Props) {
  const { layout } = node;
  const accent = layout.accent_color || "#a78bfa";

  return (
    <div
      className={`panel theme-${layout.theme || "violet"}`}
      style={{
        left: `${node.coord_x * 100}vw`,
        top: `${node.coord_y * 100}vh`,
      }}
      data-node-id={node.node_id}
    >
      <div className="panel-scroll">
      <motion.div
        className="panel-inner"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: isCurrent ? 1 : 0.85, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="panel-icon">{layout.icon}</div>
        <div className="eyebrow">{layout.eyebrow}</div>
        <h1 className="headline">
          {layout.headline}
          {layout.headline_accent && (
            <>
              <br />
              <em style={{ color: accent }}>{layout.headline_accent}</em>
            </>
          )}
        </h1>
        {layout.body && <p className="body-lg" style={{ marginTop: 18 }}>{layout.body}</p>}

        {layout.components.map((c, i) => {
          switch (c.type) {
            case "stat_grid":   return <StatGridView   key={i} block={c} />;
            case "chart":       return <ChartView      key={i} block={c} accent={accent} />;
            case "list":        return <ListView       key={i} block={c} accent={accent} />;
            case "text_block":  return <TextBlockView  key={i} block={c} />;
            case "metric_block":return <MetricBlockView key={i} block={c} accent={accent} />;
            case "tag_row":     return <TagRowView     key={i} block={c} />;
            default: return null;
          }
        })}
      </motion.div>
      </div>
    </div>
  );
}
