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

function hexToRgba(hex: string | null | undefined, alpha: number): string {
  if (!hex) return `rgba(0,0,0,${alpha})`;
  const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return `rgba(0,0,0,${alpha})`;
  let h = m[1];
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

export function NodeCard({ node, isCurrent }: Props) {
  const { layout } = node;
  const accent = layout.accent_color || "#a78bfa";

  // Build panel background:
  //  - if bg_image_url is set, use the image as the panel bg with a tinted
  //    gradient overlay so text remains readable;
  //  - else use the LLM-picked gradient;
  //  - else fall back to legacy theme class.
  const stops = [layout.bg_from, layout.bg_via, layout.bg_to].filter(Boolean) as string[];
  const gradient =
    stops.length >= 2 ? `linear-gradient(135deg, ${stops.join(", ")})` : null;

  let panelStyle: React.CSSProperties = {
    left: `${node.coord_x * 100}vw`,
    top: `${node.coord_y * 100}vh`,
  };
  let className = `panel ${gradient || layout.bg_image_url ? "" : `theme-${layout.theme || "violet"}`}`;

  if (layout.bg_image_url) {
    const fromTint = hexToRgba(layout.bg_from || "#0a0a14", 0.55);
    const toTint = hexToRgba(layout.bg_to || "#0a0a14", 0.85);
    panelStyle = {
      ...panelStyle,
      backgroundImage: `linear-gradient(135deg, ${fromTint}, ${toTint}), url(${layout.bg_image_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
    className += " has-bg-image";
  } else if (gradient) {
    panelStyle = { ...panelStyle, background: gradient };
  }

  return (
    <div className={className} style={panelStyle} data-node-id={node.node_id}>
      <div className="panel-scroll">
        <motion.div
          className="panel-inner"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: isCurrent ? 1 : 0.85, y: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="panel-icon">{layout.icon}</div>
          <div className="eyebrow">{layout.eyebrow}</div>
          <h1 className="headline">{layout.headline}</h1>
          {layout.headline_accent &&
            !layout.headline.toLowerCase().includes(layout.headline_accent.toLowerCase()) &&
            layout.headline_accent.toLowerCase() !== layout.headline.toLowerCase() && (
              <p className="headline-sub" style={{ color: accent }}>
                {layout.headline_accent}
              </p>
            )}
          {layout.body && <p className="body-lg">{layout.body}</p>}

          {layout.components.map((c, i) => {
            switch (c.type) {
              case "stat_grid":   return <StatGridView    key={i} block={c} />;
              case "chart":       return <ChartView       key={i} block={c} accent={accent} />;
              case "list":        return <ListView        key={i} block={c} accent={accent} />;
              case "text_block":  return <TextBlockView   key={i} block={c} />;
              case "metric_block":return <MetricBlockView key={i} block={c} accent={accent} />;
              case "tag_row":     return <TagRowView      key={i} block={c} />;
              default: return null;
            }
          })}
        </motion.div>
      </div>
    </div>
  );
}
