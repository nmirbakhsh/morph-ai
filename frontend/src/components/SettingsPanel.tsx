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

export function SettingsPanel() {
  const open = useStore((s) => s.settingsOpen);
  const toggle = useStore((s) => s.toggleSettings);
  const prefs = useStore((s) => s.prefs);
  const setPref = useStore((s) => s.setPref);

  if (!open) return null;
  return (
    <div className="settings-panel" role="dialog" aria-label="Morph AI settings">
      <div className="chat-header">
        <div className="chat-header-icon">⚙</div>
        <div>
          <div className="chat-header-title">Settings</div>
          <div className="chat-header-sub">Tunes future rooms — current ones stay as-is</div>
        </div>
        <button className="chat-header-close" onClick={toggle} aria-label="Close settings">✕</button>
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
      </div>
    </div>
  );
}

export type { Prefs };
