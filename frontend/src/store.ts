import { create } from "zustand";
import type { Direction, NodeRecord, Prefs } from "./types";

const DEFAULT_PREFS: Prefs = { complexity: 3, density: 3, contrast: 3 };

const PREFS_KEY = "morph_prefs";
function loadPrefs(): Prefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const raw = window.localStorage.getItem(PREFS_KEY);
    if (!raw) return DEFAULT_PREFS;
    const parsed = JSON.parse(raw);
    return {
      complexity: clampPref(parsed.complexity),
      density: clampPref(parsed.density),
      contrast: clampPref(parsed.contrast),
    };
  } catch { return DEFAULT_PREFS; }
}
function clampPref(n: unknown): number {
  const v = typeof n === "number" ? n : 3;
  return Math.max(1, Math.min(5, Math.round(v)));
}

interface PendingNav {
  parentId: string;
  direction: Direction;
  logs: string[];
}

interface State {
  sessionId: string | null;
  nodesByCoord: Record<string, NodeRecord>;        // "x,y" -> node
  nodesById: Record<string, NodeRecord>;           // node_id -> node
  currentCoord: [number, number];
  archiveOpen: boolean;
  chatOpen: boolean;
  settingsOpen: boolean;
  prefs: Prefs;
  pending: PendingNav | null;
  /** Coords currently being prefetched (avoid duplicate calls). */
  prefetching: Set<string>;

  // setters
  setSession: (id: string) => void;
  upsertNode: (n: NodeRecord) => void;
  setCurrentCoord: (c: [number, number]) => void;
  toggleArchive: () => void;
  toggleChat: () => void;
  toggleSettings: () => void;
  setPref: (key: keyof Prefs, value: number) => void;

  // pending navigation (drives the cinematic terminal)
  startPending: (parentId: string, direction: Direction) => void;
  appendPendingLog: (line: string) => void;
  clearPending: () => void;

  // prefetch tracking
  markPrefetching: (key: string) => void;
  unmarkPrefetching: (key: string) => void;

  /** Drop every node except the one at the given coord. Used after a prefs
   *  change so neighbours regenerate with the new prefs when visited. */
  pruneToCoord: (coord: [number, number]) => void;
}

export const useStore = create<State>((set) => ({
  sessionId: null,
  nodesByCoord: {},
  nodesById: {},
  currentCoord: [0, 0],
  archiveOpen: false,
  chatOpen: false,
  settingsOpen: false,
  prefs: loadPrefs(),
  pending: null,
  prefetching: new Set<string>(),

  setSession: (id) => set({ sessionId: id }),

  upsertNode: (n) =>
    set((s) => ({
      nodesByCoord: { ...s.nodesByCoord, [`${n.coord_x},${n.coord_y}`]: n },
      nodesById: { ...s.nodesById, [n.node_id]: n },
    })),

  setCurrentCoord: (c) => set({ currentCoord: c }),

  toggleArchive: () => set((s) => ({ archiveOpen: !s.archiveOpen })),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  toggleSettings: () => set((s) => ({ settingsOpen: !s.settingsOpen })),
  setPref: (key, value) =>
    set((s) => {
      const next = { ...s.prefs, [key]: clampPref(value) };
      try { window.localStorage.setItem(PREFS_KEY, JSON.stringify(next)); } catch {}
      return { prefs: next };
    }),

  startPending: (parentId, direction) =>
    set({ pending: { parentId, direction, logs: [] } }),
  appendPendingLog: (line) =>
    set((s) => (s.pending ? { pending: { ...s.pending, logs: [...s.pending.logs, line] } } : {})),
  clearPending: () => set({ pending: null }),

  markPrefetching: (key) =>
    set((s) => {
      const next = new Set(s.prefetching);
      next.add(key);
      return { prefetching: next };
    }),
  unmarkPrefetching: (key) =>
    set((s) => {
      const next = new Set(s.prefetching);
      next.delete(key);
      return { prefetching: next };
    }),

  pruneToCoord: (coord) =>
    set((s) => {
      const k = `${coord[0]},${coord[1]}`;
      const keep = s.nodesByCoord[k];
      if (!keep) return {};
      return {
        nodesByCoord: { [k]: keep },
        nodesById: { [keep.node_id]: keep },
        prefetching: new Set<string>(),
      };
    }),
}));

export const coordKey = (x: number, y: number) => `${x},${y}`;
export const dirDelta = (d: Direction): [number, number] =>
  d === "up" ? [0, -1] : d === "down" ? [0, 1] : d === "left" ? [-1, 0] : [1, 0];
