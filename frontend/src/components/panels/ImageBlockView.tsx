import { useState } from "react";
import type { ImageBlockComp } from "../../types";

export function ImageBlockView({ block }: { block: ImageBlockComp }) {
  const [errored, setErrored] = useState(false);
  if (errored) return null;
  return (
    <div className="image-block">
      <img
        src={block.src}
        alt={block.alt || ""}
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setErrored(true)}
      />
      {block.caption && (
        <div className="image-block-caption">{block.caption}</div>
      )}
    </div>
  );
}
