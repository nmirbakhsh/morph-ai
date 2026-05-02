import type { ListBlock } from "../../types";

export function ListView({ block, accent }: { block: ListBlock; accent: string }) {
  return (
    <div className="list-wrap">
      {block.title && <div className="list-title">{block.title}</div>}
      {block.items.map((it, i) => (
        <div className="list-item" key={i}>
          {it.icon && <span className="list-item-icon">{it.icon}</span>}
          <div>
            <div className="list-item-title">{it.title}</div>
            {it.subtitle && <div className="list-item-sub">{it.subtitle}</div>}
          </div>
          {it.value && (
            <div className="list-item-value" style={{ color: accent }}>
              {it.value}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
