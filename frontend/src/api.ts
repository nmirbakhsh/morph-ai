import type {
  ChatResponse, Direction, GraphResponse, InitResponse, NavigateResponse,
} from "./types";

const BASE = "/api";

/** Viewport hint — used by the backend to tune content density per device. */
function viewport() {
  return {
    viewport_w: typeof window !== "undefined" ? window.innerWidth : null,
    viewport_h: typeof window !== "undefined" ? window.innerHeight : null,
  };
}

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  init: () =>
    jsonFetch<InitResponse>("/init", {
      method: "POST",
      body: JSON.stringify(viewport()),
    }),

  navigate: (req: {
    session_id: string;
    parent_node_id: string;
    direction: Direction;
    intent_prompt: string;
    mcp_tool?: string | null;
    prefetch?: boolean;
  }) =>
    jsonFetch<NavigateResponse>("/navigate", {
      method: "POST",
      body: JSON.stringify({ ...req, ...viewport() }),
    }),

  chat: (req: { session_id: string; current_node_id: string; message: string }) =>
    jsonFetch<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ ...req, ...viewport() }),
    }),

  graph: (sessionId: string) =>
    jsonFetch<GraphResponse>(`/graph/${sessionId}`),

  /** Build an EventSource URL for the SSE log stream of an in-flight navigate. */
  streamUrl: (parentId: string, direction: Direction) =>
    `${BASE}/stream?parent_node_id=${encodeURIComponent(parentId)}&direction=${direction}`,
};
