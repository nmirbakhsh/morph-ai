import type { IntentSignpost } from "../types";

interface Props {
  intents: IntentSignpost[];
  onPick: (intent: IntentSignpost) => void;
}

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
          aria-label={`${it.label}: ${it.sublabel}`}
          title={it.sublabel ? `${it.label} — ${it.sublabel}` : it.label}
        >
          <span className="signpost-label">{it.label}</span>
        </div>
      ))}
    </>
  );
}
