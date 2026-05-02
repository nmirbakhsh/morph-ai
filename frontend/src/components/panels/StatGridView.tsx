import type { StatGrid } from "../../types";

export function StatGridView({ block }: { block: StatGrid }) {
  return (
    <div className="stat-grid">
      {block.items.map((it, i) => (
        <div className="stat-card" key={i}>
          <div className="stat-label">{it.label}</div>
          <div className="stat-value">{it.value}</div>
          {it.delta && (
            <div className={`stat-delta ${it.trend ?? "flat"}`}>
              {it.trend === "up" ? "↑ " : it.trend === "down" ? "↓ " : "· "}
              {it.delta}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
