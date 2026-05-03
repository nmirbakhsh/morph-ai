import { useState } from "react";
import type { ImageBlockComp } from "../../types";

/**
 * Inline image rendered in a fixed-aspect tile. We use a div with
 * `background-image` + `background-size: cover` rather than an <img> so
 * any source image fits the slot regardless of its native dimensions —
 * we crop what doesn't fit and show what we can.
 */
export function ImageBlockView({ block }: { block: ImageBlockComp }) {
  const [errored, setErrored] = useState(false);
  if (errored) return null;
  return (
    <div className="image-block">
      <div
        className="image-block-fit"
        style={{ backgroundImage: `url(${JSON.stringify(block.src).slice(1, -1)})` }}
        role="img"
        aria-label={block.alt || block.caption || "image"}
      />
      {/* Hidden eager loader so onError fires for broken sources, hiding the block. */}
      <img
        src={block.src}
        alt=""
        onError={() => setErrored(true)}
        style={{ display: "none" }}
        referrerPolicy="no-referrer"
      />
      {block.caption && <div className="image-block-caption">{block.caption}</div>}
    </div>
  );
}
