import type { TextBlock } from "../../types";

export function TextBlockView({ block }: { block: TextBlock }) {
  return (
    <div className="text-block">
      {block.title && <div className="text-block-title">{block.title}</div>}
      <div className="text-block-body">{block.body}</div>
    </div>
  );
}
