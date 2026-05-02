const BASE = "/api";
async function jsonFetch(path, init) {
    const res = await fetch(BASE + path, {
        ...init,
        headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    if (!res.ok)
        throw new Error(`${res.status} ${await res.text()}`);
    return res.json();
}
export const api = {
    init: () => jsonFetch("/init", { method: "POST" }),
    navigate: (req) => jsonFetch("/navigate", {
        method: "POST",
        body: JSON.stringify(req),
    }),
    chat: (req) => jsonFetch("/chat", {
        method: "POST",
        body: JSON.stringify(req),
    }),
    graph: (sessionId) => jsonFetch(`/graph/${sessionId}`),
    /** Build an EventSource URL for the SSE log stream of an in-flight navigate. */
    streamUrl: (parentId, direction) => `${BASE}/stream?parent_node_id=${encodeURIComponent(parentId)}&direction=${direction}`,
};
