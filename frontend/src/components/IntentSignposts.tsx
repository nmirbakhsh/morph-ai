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
      {intents.map((it) => {
        const arrow = ARROWS[it.direction];
        return (
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
            aria-label={`${arrow} ${it.label}: ${it.sublabel}`}
            title={`${it.label} — ${it.sublabel}`}
          >
            <div className="signpost-body">
              {(it.direction === "left" || it.direction === "up") && (
                <span className="signpost-arrow">{arrow}</span>
              )}
              <span className="signpost-icon">{it.icon}</span>
              <div className="signpost-text">
                <span className="signpost-label">{it.label}</span>
                <span className="signpost-sub">{it.sublabel}</span>
              </div>
              {(it.direction === "right" || it.direction === "down") && (
                <span className="signpost-arrow">{arrow}</span>
              )}
            </div>
          </div>
        );
      })}
    </>
  );
}
