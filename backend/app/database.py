"""SQLite-backed DAG storage. Sessions own a tree of nodes via parent_node_id."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, List, Optional

from .config import DATABASE_PATH
from .schemas import (
    AdjacentIntents, Direction, NodeLayout, NodeRecord,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir() -> None:
    parent = os.path.dirname(DATABASE_PATH)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def init_db() -> None:
    _ensure_dir()
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            cookie_context TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            parent_node_id TEXT,
            direction_from_parent TEXT,
            coord_x INTEGER NOT NULL DEFAULT 0,
            coord_y INTEGER NOT NULL DEFAULT 0,
            mcp_tool_executed TEXT,
            title TEXT NOT NULL,
            layout_json TEXT NOT NULL,
            adjacent_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id),
            FOREIGN KEY (parent_node_id) REFERENCES nodes(node_id)
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_session ON nodes(session_id);
        CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_node_id);
        """)


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    _ensure_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ─── Sessions ─────────────────────────────────────────────────────────────

def create_session(cookie_context: dict | None = None) -> str:
    sid = str(uuid.uuid4())
    with _conn() as c:
        c.execute(
            "INSERT INTO sessions(session_id, cookie_context, created_at) VALUES(?,?,?)",
            (sid, json.dumps(cookie_context or {}), _now()),
        )
    return sid


# ─── Nodes ────────────────────────────────────────────────────────────────

def _row_to_node(row: sqlite3.Row) -> NodeRecord:
    return NodeRecord(
        node_id=row["node_id"],
        session_id=row["session_id"],
        parent_node_id=row["parent_node_id"],
        direction_from_parent=row["direction_from_parent"],
        coord_x=row["coord_x"],
        coord_y=row["coord_y"],
        mcp_tool_executed=row["mcp_tool_executed"],
        title=row["title"],
        layout=NodeLayout.model_validate_json(row["layout_json"]),
        adjacent_intents=AdjacentIntents.model_validate_json(row["adjacent_json"]),
        created_at=row["created_at"],
    )


def update_node_layout(
    *, node_id: str, title: str, layout: NodeLayout, adjacent_intents: AdjacentIntents,
) -> Optional[NodeRecord]:
    """Replace a node's layout + intents in place. Used by /api/regenerate."""
    with _conn() as c:
        c.execute(
            """UPDATE nodes
               SET title = ?, layout_json = ?, adjacent_json = ?
             WHERE node_id = ?""",
            (title, layout.model_dump_json(),
             adjacent_intents.model_dump_json(), node_id),
        )
    return get_node(node_id)


def insert_node(
    *,
    session_id: str,
    parent_node_id: Optional[str],
    direction_from_parent: Optional[Direction],
    coord_x: int,
    coord_y: int,
    mcp_tool_executed: Optional[str],
    title: str,
    layout: NodeLayout,
    adjacent_intents: AdjacentIntents,
) -> NodeRecord:
    nid = str(uuid.uuid4())
    created_at = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO nodes(
                node_id, session_id, parent_node_id, direction_from_parent,
                coord_x, coord_y, mcp_tool_executed, title,
                layout_json, adjacent_json, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                nid, session_id, parent_node_id, direction_from_parent,
                coord_x, coord_y, mcp_tool_executed, title,
                layout.model_dump_json(), adjacent_intents.model_dump_json(),
                created_at,
            ),
        )
    return NodeRecord(
        node_id=nid,
        session_id=session_id,
        parent_node_id=parent_node_id,
        direction_from_parent=direction_from_parent,
        coord_x=coord_x,
        coord_y=coord_y,
        mcp_tool_executed=mcp_tool_executed,
        title=title,
        layout=layout,
        adjacent_intents=adjacent_intents,
        created_at=created_at,
    )


def get_node(node_id: str) -> Optional[NodeRecord]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM nodes WHERE node_id = ?", (node_id,)
        ).fetchone()
    return _row_to_node(row) if row else None


def get_session_nodes(session_id: str) -> List[NodeRecord]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM nodes WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [_row_to_node(r) for r in rows]


def find_node_at_coord(session_id: str, x: int, y: int) -> Optional[NodeRecord]:
    """Reuse a node if user navigates back to a coordinate that already exists."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM nodes WHERE session_id = ? AND coord_x = ? AND coord_y = ?",
            (session_id, x, y),
        ).fetchone()
    return _row_to_node(row) if row else None
