import { create } from "zustand";
import type { Direction, NodeRecord } from "./types";

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
  pending: PendingNav | null;
  /** Coords currently being prefetched (avoid duplicate calls). */
  prefetching: Set<string>;

  // setters
  setSession: (id: string) => void;
  upsertNode: (n: NodeRecord) => void;
  setCurrentCoord: (c: [number, number]) => void;
  toggleArchive: () => void;
  toggleChat: () => void;

  // pending navigation (drives the cinematic terminal)
  startPending: (parentId: string, direction: Direction) => void;
  appendPendingLog: (line: string) => void;
  clearPending: () => void;

  // prefetch tracking
  markPrefetching: (key: string) => void;
  unmarkPrefetching: (key: string) => void;
}

export const useStore = create<State>((set) => ({
  sessionId: null,
  nodesByCoord: {},
  nodesById: {},
  currentCoord: [0, 0],
  archiveOpen: false,
  chatOpen: false,
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
}));

export const coordKey = (x: number, y: number) => `${x},${y}`;
export const dirDelta = (d: Direction): [number, number] =>
  d === "up" ? [0, -1] : d === "down" ? [0, 1] : d === "left" ? [-1, 0] : [1, 0];
