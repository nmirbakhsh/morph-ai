import type { Direction, IntentSignpost } from "../types";

interface Props {
  intents: IntentSignpost[];
  onPick: (intent: IntentSignpost) => void;
}

const ARROWS: Record<Direction, string> = {
  up: "↑", down: "↓", left: "←", right: "→",
};

export function IntentSignposts({ intents, onPick }: Props) {
  return (
    <>
      {intents.map((it) => (
        <div
          key={it.direction}
          className={[
            "signpost", it.direction,
            it.is_back ? "is-back" : "",
            it.is_continuation ? "is-continuation" : "",
          ].filter(Boolean).join(" ")}
          onClick={() => onPick(it)}
          role="button"
          tabIndex={0}
        >
          {(it.direction === "up" || it.direction === "left") && (
            <div className="signpost-arrow">{ARROWS[it.direction]}</div>
          )}
          <div className="signpost-icon">{it.icon}</div>
          <div className="signpost-label">{it.label}</div>
          <div className="signpost-sub">{it.sublabel}</div>
          {(it.direction === "down" || it.direction === "right") && (
            <div className="signpost-arrow">{ARROWS[it.direction]}</div>
          )}
        </div>
      ))}
    </>
  );
}
