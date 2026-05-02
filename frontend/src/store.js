import { create } from "zustand";
export const useStore = create((set) => ({
    sessionId: null,
    nodesByCoord: {},
    nodesById: {},
    currentCoord: [0, 0],
    archiveOpen: false,
    chatOpen: false,
    pending: null,
    prefetching: new Set(),
    setSession: (id) => set({ sessionId: id }),
    upsertNode: (n) => set((s) => ({
        nodesByCoord: { ...s.nodesByCoord, [`${n.coord_x},${n.coord_y}`]: n },
        nodesById: { ...s.nodesById, [n.node_id]: n },
    })),
    setCurrentCoord: (c) => set({ currentCoord: c }),
    toggleArchive: () => set((s) => ({ archiveOpen: !s.archiveOpen })),
    toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
    startPending: (parentId, direction) => set({ pending: { parentId, direction, logs: [] } }),
    appendPendingLog: (line) => set((s) => (s.pending ? { pending: { ...s.pending, logs: [...s.pending.logs, line] } } : {})),
    clearPending: () => set({ pending: null }),
    markPrefetching: (key) => set((s) => {
        const next = new Set(s.prefetching);
        next.add(key);
        return { prefetching: next };
    }),
    unmarkPrefetching: (key) => set((s) => {
        const next = new Set(s.prefetching);
        next.delete(key);
        return { prefetching: next };
    }),
}));
export const coordKey = (x, y) => `${x},${y}`;
export const dirDelta = (d) => d === "up" ? [0, -1] : d === "down" ? [0, 1] : d === "left" ? [-1, 0] : [1, 0];
