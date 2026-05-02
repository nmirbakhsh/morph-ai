import type { TagRow } from "../../types";

export function TagRowView({ block }: { block: TagRow }) {
  return (
    <div className="tag-row">
      {block.tags.map((t, i) => (
        <span className="tag" key={i}>{t}</span>
      ))}
    </div>
  );
}
