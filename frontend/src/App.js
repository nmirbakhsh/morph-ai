import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useCallback, useEffect, useRef } from "react";
import { api } from "./api";
import { ArchiveMacroView } from "./components/ArchiveMacroView";
import { ChatPanel } from "./components/ChatPanel";
import { IntentSignposts } from "./components/IntentSignposts";
import { SpatialCanvas } from "./components/SpatialCanvas";
import { Terminal } from "./components/Terminal";
import { TopBar } from "./components/TopBar";
import { coordKey, dirDelta, useStore } from "./store";
const WHEEL_THRESHOLD = 80;
const TOUCH_THRESHOLD = 60;
export default function App() {
    const sessionId = useStore((s) => s.sessionId);
    const setSession = useStore((s) => s.setSession);
    const upsertNode = useStore((s) => s.upsertNode);
    const currentCoord = useStore((s) => s.currentCoord);
    const setCurrentCoord = useStore((s) => s.setCurrentCoord);
    const nodesByCoord = useStore((s) => s.nodesByCoord);
    const pending = useStore((s) => s.pending);
    const startPending = useStore((s) => s.startPending);
    const appendLog = useStore((s) => s.appendPendingLog);
    const clearPending = useStore((s) => s.clearPending);
    const archiveOpen = useStore((s) => s.archiveOpen);
    const navLockRef = useRef(false);
    const wheelAccumRef = useRef({ x: 0, y: 0 });
    const initStartedRef = useRef(false);
    // ── Init session on mount ──────────────────────────────────────────
    useEffect(() => {
        if (initStartedRef.current || sessionId)
            return;
        initStartedRef.current = true;
        api.init().then((res) => {
            setSession(res.session_id);
            upsertNode(res.node);
            setCurrentCoord([res.node.coord_x, res.node.coord_y]);
        }).catch((e) => {
            initStartedRef.current = false;
            console.error("init failed", e);
        });
    }, [sessionId, setSession, upsertNode, setCurrentCoord]);
    const currentNode = nodesByCoord[coordKey(currentCoord[0], currentCoord[1])];
    // ── Navigation logic ───────────────────────────────────────────────
    const goDirection = useCallback(async (direction, intent) => {
        if (navLockRef.current || archiveOpen)
            return;
        if (!currentNode || !sessionId)
            return;
        const adj = currentNode.adjacent_intents.intents;
        const picked = intent || adj.find((i) => i.direction === direction);
        // Back / target_node_id: just shift coords to the target.
        if (picked?.target_node_id) {
            const target = useStore.getState().nodesById[picked.target_node_id];
            if (target) {
                navLockRef.current = true;
                setCurrentCoord([target.coord_x, target.coord_y]);
                setTimeout(() => { navLockRef.current = false; }, 720);
                return;
            }
        }
        const [dx, dy] = dirDelta(direction);
        const nextCoord = [
            currentNode.coord_x + dx, currentNode.coord_y + dy,
        ];
        const existing = nodesByCoord[coordKey(...nextCoord)];
        if (existing) {
            // Either prefetched or visited — instant pan.
            navLockRef.current = true;
            setCurrentCoord(nextCoord);
            setTimeout(() => { navLockRef.current = false; }, 720);
            return;
        }
        if (!picked)
            return;
        navLockRef.current = true;
        startPending(currentNode.node_id, direction);
        // Open SSE for the cinematic terminal. Backend queue is created when
        // /navigate starts; the SSE handler polls briefly for it to appear.
        const es = new EventSource(api.streamUrl(currentNode.node_id, direction));
        es.addEventListener("log", (e) => appendLog(e.data));
        es.addEventListener("done", () => es.close());
        es.addEventListener("error", () => es.close());
        try {
            const res = await api.navigate({
                session_id: sessionId,
                parent_node_id: currentNode.node_id,
                direction,
                intent_prompt: picked.intent_prompt,
                mcp_tool: picked.mcp_tool ?? null,
            });
            upsertNode(res.node);
            setTimeout(() => {
                setCurrentCoord([res.node.coord_x, res.node.coord_y]);
                clearPending();
                navLockRef.current = false;
            }, 400);
        }
        catch (e) {
            console.error("navigate failed", e);
            es.close();
            clearPending();
            navLockRef.current = false;
        }
    }, [archiveOpen, sessionId, currentNode, nodesByCoord,
        startPending, appendLog, upsertNode, setCurrentCoord, clearPending]);
    // ── Parallel prefetch of the 3 forward directions ─────────────────
    // After landing on a node, materialize neighbors in the background so the
    // next navigation feels instant. Depth-1 only (no recursion).
    useEffect(() => {
        if (!currentNode || !sessionId)
            return;
        const state = useStore.getState();
        for (const intent of currentNode.adjacent_intents.intents) {
            if (intent.is_back || intent.target_node_id)
                continue;
            const [dx, dy] = dirDelta(intent.direction);
            const nx = currentNode.coord_x + dx;
            const ny = currentNode.coord_y + dy;
            const k = coordKey(nx, ny);
            if (state.nodesByCoord[k])
                continue;
            if (state.prefetching.has(k))
                continue;
            state.markPrefetching(k);
            api.navigate({
                session_id: sessionId,
                parent_node_id: currentNode.node_id,
                direction: intent.direction,
                intent_prompt: intent.intent_prompt,
                mcp_tool: intent.mcp_tool ?? null,
                prefetch: true,
            })
                .then((res) => {
                useStore.getState().upsertNode(res.node);
            })
                .catch((e) => console.warn("prefetch failed", intent.direction, e))
                .finally(() => useStore.getState().unmarkPrefetching(k));
        }
    }, [currentNode, sessionId]);
    // ── Wheel ─────────────────────────────────────────────────────────
    useEffect(() => {
        const onWheel = (e) => {
            if (archiveOpen)
                return;
            e.preventDefault();
            if (navLockRef.current)
                return;
            const acc = wheelAccumRef.current;
            acc.x += e.deltaX;
            acc.y += e.deltaY;
            let dir = null;
            if (Math.abs(acc.x) > Math.abs(acc.y)) {
                if (acc.x > WHEEL_THRESHOLD)
                    dir = "right";
                else if (acc.x < -WHEEL_THRESHOLD)
                    dir = "left";
            }
            else {
                if (acc.y > WHEEL_THRESHOLD)
                    dir = "down";
                else if (acc.y < -WHEEL_THRESHOLD)
                    dir = "up";
            }
            if (dir) {
                wheelAccumRef.current = { x: 0, y: 0 };
                goDirection(dir);
            }
        };
        window.addEventListener("wheel", onWheel, { passive: false });
        return () => window.removeEventListener("wheel", onWheel);
    }, [goDirection, archiveOpen]);
    // ── Keyboard ──────────────────────────────────────────────────────
    useEffect(() => {
        const onKey = (e) => {
            if (archiveOpen) {
                if (e.key === "Escape")
                    useStore.getState().toggleArchive();
                return;
            }
            // ignore keys while typing in chat
            const tag = e.target?.tagName;
            if (tag === "INPUT" || tag === "TEXTAREA")
                return;
            switch (e.key) {
                case "ArrowRight":
                    goDirection("right");
                    break;
                case "ArrowLeft":
                    goDirection("left");
                    break;
                case "ArrowDown":
                    goDirection("down");
                    break;
                case "ArrowUp":
                    goDirection("up");
                    break;
                case "a":
                    useStore.getState().toggleArchive();
                    break;
                case "/":
                    e.preventDefault();
                    useStore.getState().toggleChat();
                    break;
            }
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [goDirection, archiveOpen]);
    // ── Touch / swipe ─────────────────────────────────────────────────
    useEffect(() => {
        let sx = 0, sy = 0, active = false;
        const onStart = (e) => {
            sx = e.touches[0].clientX;
            sy = e.touches[0].clientY;
            active = true;
        };
        const onEnd = (e) => {
            if (!active)
                return;
            active = false;
            const dx = e.changedTouches[0].clientX - sx;
            const dy = e.changedTouches[0].clientY - sy;
            let dir = null;
            if (Math.abs(dx) > Math.abs(dy)) {
                if (dx > TOUCH_THRESHOLD)
                    dir = "left";
                else if (dx < -TOUCH_THRESHOLD)
                    dir = "right";
            }
            else {
                if (dy > TOUCH_THRESHOLD)
                    dir = "up";
                else if (dy < -TOUCH_THRESHOLD)
                    dir = "down";
            }
            if (dir)
                goDirection(dir);
        };
        document.addEventListener("touchstart", onStart, { passive: true });
        document.addEventListener("touchend", onEnd, { passive: true });
        return () => {
            document.removeEventListener("touchstart", onStart);
            document.removeEventListener("touchend", onEnd);
        };
    }, [goDirection]);
    return (_jsxs(_Fragment, { children: [_jsx(SpatialCanvas, {}), _jsx(TopBar, { panelLabel: currentNode?.title ?? "Loading…" }), currentNode && !pending && (_jsx(IntentSignposts, { intents: currentNode.adjacent_intents.intents, onPick: (it) => goDirection(it.direction, it) })), pending && _jsx(Terminal, { logs: pending.logs }), _jsx(ChatPanel, {}), _jsx(ArchiveMacroView, {}), _jsxs("div", { className: "coord-readout", children: ["XY ", currentCoord[0], ", ", currentCoord[1], currentNode ? ` · ${currentNode.title}` : ""] })] }));
}
