import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import type { Prefs } from "../types";

const COMPLEXITY_LABELS = ["ELI5", "Casual", "Balanced", "Technical", "Expert"];
const DENSITY_LABELS    = ["Spartan", "Sparse", "Balanced", "Dense", "Packed"];
const CONTRAST_LABELS   = ["Subtle", "Soft", "Balanced", "Bold", "Sharp"];

interface SliderProps {
  label: string;
  hint: string;
  value: number;
  onChange: (v: number) => void;
  marks: string[];
}

function Slider({ label, hint, value, onChange, marks }: SliderProps) {
  return (
    <div className="settings-row">
      <div className="settings-row-head">
        <span className="settings-row-label">{label}</span>
        <span className="settings-row-value">{marks[value - 1]}</span>
      </div>
      <input
        type="range"
        min={1}
        max={5}
        step={1}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="settings-slider"
      />
      <div className="settings-row-hint">{hint}</div>
    </div>
  );
}

function prefsEqual(a: Prefs, b: Prefs): boolean {
  return a.complexity === b.complexity
      && a.density === b.density
      && a.contrast === b.contrast;
}

export function SettingsPanel() {
  const open = useStore((s) => s.settingsOpen);
  const toggle = useStore((s) => s.toggleSettings);
  const prefs = useStore((s) => s.prefs);
  const setPref = useStore((s) => s.setPref);
  const upsertNode = useStore((s) => s.upsertNode);
  const pruneToCoord = useStore((s) => s.pruneToCoord);

  // Snapshot prefs at open-time so we can detect changes on close.
  const snapshotRef = useRef<Prefs | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    if (open && !snapshotRef.current) {
      snapshotRef.current = { ...prefs };
    }
  }, [open, prefs]);

  const closeAndMaybeReload = async () => {
    const snap = snapshotRef.current;
    snapshotRef.current = null;
    toggle();

    if (!snap || prefsEqual(snap, prefs)) return;

    // Prefs changed — regenerate the current node and drop prefetched neighbours.
    const state = useStore.getState();
    const [cx, cy] = state.currentCoord;
    const current = state.nodesByCoord[`${cx},${cy}`];
    if (!current) return;

    setRegenerating(true);
    try {
      const res = await api.regenerate(current.node_id);
      upsertNode(res.node);
      pruneToCoord([cx, cy]);
    } catch (e) {
      console.error("regenerate failed", e);
    } finally {
      setRegenerating(false);
    }
  };

  if (!open && !regenerating) return null;
  return (
    <div className="settings-panel" role="dialog" aria-label="Morph AI settings">
      <div className="chat-header">
        <div className="chat-header-icon">⚙</div>
        <div>
          <div className="chat-header-title">Settings</div>
          <div className="chat-header-sub">
            {regenerating ? "Reloading current room…" : "Close to apply to the current room"}
          </div>
        </div>
        <button
          className="chat-header-close"
          onClick={closeAndMaybeReload}
          aria-label="Close settings"
          disabled={regenerating}
        >
          ✕
        </button>
      </div>

      <div className="settings-body">
        <Slider
          label="Complexity"
          hint="How technical the language gets"
          value={prefs.complexity}
          onChange={(v) => setPref("complexity", v)}
          marks={COMPLEXITY_LABELS}
        />
        <Slider
          label="Density"
          hint="How much content fits per slide"
          value={prefs.density}
          onChange={(v) => setPref("density", v)}
          marks={DENSITY_LABELS}
        />
        <Slider
          label="Color contrast"
          hint="How sharp the gradient between rooms feels"
          value={prefs.contrast}
          onChange={(v) => setPref("contrast", v)}
          marks={CONTRAST_LABELS}
        />
        {regenerating && (
          <div className="settings-regen-status">
            <div className="typing-dots"><span /><span /><span /></div>
            <span>Regenerating current room with new settings…</span>
          </div>
        )}
      </div>
    </div>
  );
}

export type { Prefs };
