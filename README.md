# Morph AI — Spatial MCP Canvas

A self-hosted, containerized app that bridges any number of [Model Context
Protocol](https://modelcontextprotocol.io) servers, asks an LLM to translate
their tools and outputs into a **spatial graph of rooms**, and lets the user
explore in four directions (or teleport via natural language).

```
                        [ ↑ next room ]
                              │
[ ← next room ] ───────  current room  ─────── [ → next room ]
                              │
                        [ ↓ next room ]
```

Each room is a full-bleed panel. The four edges hint at AI-suggested rooms.
Scroll, swipe, or arrow-key in any direction and a new room is generated
on-demand from the connected MCP servers. A glassy "Ask Morph" chat lets you
teleport to a completely different room at any time.

---

## Stack

| Layer        | Tech                                            |
| ------------ | ----------------------------------------------- |
| Orchestrator | Docker Compose                                  |
| Backend      | Python 3.11 · FastAPI · SQLite · MCP SDK · SSE  |
| LLM          | Gemini (default `gemini-3.1-flash-lite-preview`)       |
| Frontend     | React 18 · TypeScript · Vite · Zustand · Framer Motion |

---

## Quickstart

```bash
cd morph-ai
cp .env.example .env          # then edit GEMINI_API_KEY
docker compose up --build
```

- Backend: <http://localhost:8000>  (`/api/health` for liveness + MCP status)
- Frontend: <http://localhost:3000>

---

## Configuration

### `.env`

```env
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.1-flash-lite-preview   # any Gemini model id
DATABASE_PATH=/data/morph.db
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### `config.yaml` — MCP servers

Each entry spawns an MCP server as a stdio subprocess. Both Python (`uvx`) and
Node (`npx`) launchers are supported because the backend image installs both.

```yaml
mcp_servers:
  - name: wikipedia
    transport: stdio
    command: uvx
    args: ["wikipedia-mcp-server@latest"]
    enabled: true

  # Add more — examples:
  # - name: filesystem
  #   transport: stdio
  #   command: npx
  #   args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
```

Restart the backend after changing this file.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          docker-compose                             │
│                                                                     │
│  ┌──────────────────┐         ┌────────────────────────────┐        │
│  │   frontend       │ ◀─api─▶ │   backend (FastAPI)        │        │
│  │  React + Vite    │         │                            │        │
│  │  Spatial canvas  │         │  • config_loader.py        │        │
│  │  Framer + Zustand│         │  • mcp_client.py  ◀── stdio ─┐      │
│  │  EventSource SSE │         │  • tool_registry.py         ├─┐    │
│  │                  │         │  • llm_engine.py (Gemini)   │ │    │
│  │                  │         │  • routes/                  │ │    │
│  │                  │         │  • SQLite (DAG of nodes)    │ │    │
│  └──────────────────┘         └────────────────────────────┘ │ │    │
│                                                              ▼ ▼    │
│                                              [ MCP server  ] [ ... ]│
└─────────────────────────────────────────────────────────────────────┘
```

### Data model

```
sessions(session_id PK, cookie_context, created_at)
nodes(node_id PK, session_id FK, parent_node_id FK,
      direction_from_parent, coord_x, coord_y,
      mcp_tool_executed, title,
      layout_json, adjacent_json, created_at)
```

The DAG is keyed by `parent_node_id`. An (x,y) coord is also stored so the
frontend can lay out the spatial canvas without re-traversing the graph.

### LLM strategy (two prompts)

- **Prompt A — Intents.** After every successful node materialization, ask
  Gemini to suggest the four directional next rooms. Output is a strict
  Pydantic `AdjacentIntents` (1-4 signposts, one per direction).
- **Prompt B — Layout.** When the user enters a new direction, the chosen
  MCP tool is called (if any), then Gemini translates its raw output into a
  strict `NodeLayout` (theme, accent, eyebrow, headline, components).

Components currently supported by the schema:

| Component      | Use                                  |
| -------------- | ------------------------------------ |
| `stat_grid`    | 3-up KPI cards with optional deltas  |
| `chart`        | Sparkline with hero number / delta   |
| `list`         | Vertical list with icons + values    |
| `text_block`   | Prose narrative                      |
| `metric_block` | One huge number                      |
| `tag_row`      | Pill row of short labels             |

### API endpoints

| Method | Path                       | Purpose                              |
| ------ | -------------------------- | ------------------------------------ |
| `POST` | `/api/init`                | Start session, generate origin node  |
| `POST` | `/api/navigate`            | Generate the next room in a direction|
| `GET`  | `/api/stream`              | SSE log stream (cinematic terminal)  |
| `GET`  | `/api/graph/{session_id}`  | Full DAG for the archive view        |
| `POST` | `/api/chat`                | Natural-language teleport / explain  |
| `GET`  | `/api/health`              | Liveness + MCP server status         |

---

## Frontend behaviour

- **Wheel / trackpad** — accumulated delta past 80px snaps in the dominant axis.
- **Arrow keys** — instant directional navigation.
- **Touch** — swipe past 60px in any direction.
- **`/`** — toggle chat panel.
- **`a`** — open archive (zoom-out DAG view); `Esc` to close.
- **`Ask Morph` chat** — sends `{message, current_node_id}` to `/api/chat`.
  The LLM either replies in chat or returns a brand-new teleport node that gets
  inserted into the canvas at a fresh diagonal coord.

While a navigation is in flight, a **cinematic terminal** overlay streams the
backend's per-step logs (intent → tool args → tool result → layout → intents)
via SSE.

---

## Local development without Docker

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
GEMINI_API_KEY=… uvicorn app.main:app --reload --port 8000

# frontend (in another shell)
cd frontend
npm install
npm run dev
```

Frontend talks to the backend via Vite's `/api` proxy, configured to
`VITE_API_BASE` (default `http://localhost:8000`).

---

## Adding a new MCP server

1. Add an entry to `config.yaml`.
2. Restart the backend container.
3. Hit `GET /api/health` — your new server should appear in `mcp_servers` and
   its tools in `tools`.
4. The next time the LLM generates intents (Prompt A), it will see the new
   tools in the registry and may route a direction through one of them.

No frontend changes required — the spatial canvas adapts to whatever the LLM
emits.
