import type { ChartBlock } from "../../types";

export function ChartView({ block, accent }: { block: ChartBlock; accent: string }) {
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

  return (
    <div className="chart-wrap">
      <div className="chart-header">
        <div>
          <div className="chart-title">{block.title}</div>
          {block.subtitle && <div className="chart-sub">{block.subtitle}</div>}
        </div>
        {(block.hero_value || block.hero_delta) && (
          <div style={{ textAlign: "right" }}>
            {block.hero_value && <div className="chart-hero-val">{block.hero_value}</div>}
            {block.hero_delta && (
              <div className="chart-hero-delta" style={{ color: accent }}>
                {block.hero_delta}
              </div>
            )}
          </div>
        )}
      </div>
      <svg className="sparkline" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity="0.35" />
            <stop offset="100%" stopColor={accent} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#${gradId})`} />
        <path d={linePath} fill="none" stroke={accent} strokeWidth={2.5} strokeLinejoin="round" />
      </svg>
    </div>
  );
}
