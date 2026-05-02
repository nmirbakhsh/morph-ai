import type { MetricBlock } from "../../types";

export function MetricBlockView({ block, accent }: { block: MetricBlock; accent: string }) {
  return (
    <div className="metric-block">
      <div className="metric-block-label">{block.label}</div>
      <div className="metric-block-value" style={{ color: accent }}>{block.value}</div>
      {block.sublabel && <div className="metric-block-sub">{block.sublabel}</div>}
    </div>
  );
}
