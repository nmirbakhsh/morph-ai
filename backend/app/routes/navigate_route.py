"""POST /api/navigate — generate the room in a chosen direction."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..llm_engine import (
    OPPOSITE, generate_adjacent_intents, generate_layout,
    make_back_intent, synthesize_mcp_args,
)
from ..mcp_client import bridge
from ..schemas import Direction, NavigateRequest, NavigateResponse

router = APIRouter()


_DIR_DELTAS: Dict[str, tuple[int, int]] = {
    "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
}


# Track in-flight navigate jobs so /api/stream/{node_id} can subscribe to logs.
# Maps a parent_node_id+direction key to an asyncio.Queue of log lines.
_streams: Dict[str, asyncio.Queue[str]] = {}


def stream_key(parent_node_id: str, direction: Direction) -> str:
    return f"{parent_node_id}:{direction}"


async def _push(key: str, line: str) -> None:
    q = _streams.get(key)
    if q is not None:
        await q.put(line)


@router.post("/navigate", response_model=NavigateResponse)
async def navigate_endpoint(req: NavigateRequest) -> NavigateResponse:
    parent = db.get_node(req.parent_node_id)
    if not parent:
        raise HTTPException(404, "parent node not found")

    dx, dy = _DIR_DELTAS[req.direction]
    nx, ny = parent.coord_x + dx, parent.coord_y + dy

    existing = db.find_node_at_coord(parent.session_id, nx, ny)
    if existing:
        return NavigateResponse(node=existing)

    # Suppress streaming when the caller is prefetching in the background.
    silent = bool(req.prefetch)
    key = stream_key(req.parent_node_id, req.direction) if not silent else None
    if key:
        _streams[key] = asyncio.Queue()
    sent_done = False
    try:
        if key:
            await _push(key, f"$ morph navigate --dir {req.direction}")
            await _push(key, f"▶ intent: {req.intent_prompt}")

        mcp_output: Optional[Dict[str, Any]] = None
        if req.mcp_tool and req.mcp_tool in {t["qualified_name"] for t in bridge.list_tools()}:
            tool_meta = next(
                t for t in bridge.list_tools() if t["qualified_name"] == req.mcp_tool
            )
            if key: await _push(key, f"▶ resolving tool: {req.mcp_tool}")
            args = await synthesize_mcp_args(
                tool_qualified_name=req.mcp_tool,
                intent_prompt=req.intent_prompt,
                tool_schema=tool_meta["input_schema"],
            )
            if key: await _push(key, f"▶ args: {json.dumps(args)[:200]}")
            try:
                mcp_output = await bridge.call_tool(req.mcp_tool, args)
                if key: await _push(key, "✓ tool returned")
            except Exception as e:  # noqa: BLE001
                if key: await _push(key, f"✗ tool error: {e}")

        if key: await _push(key, "▶ generating layout (Prompt B)…")
        layout = await generate_layout(
            intent_prompt=req.intent_prompt,
            mcp_tool=req.mcp_tool,
            mcp_output=mcp_output,
            parent_title=parent.title,
        )
        if key: await _push(key, "✓ layout ready")

        if key: await _push(key, "▶ projecting next intents (Prompt A)…")
        history_titles = [n.title for n in db.get_session_nodes(parent.session_id)]

        # Reserve the OPPOSITE direction for a synthetic Back signpost
        # pointing to the parent node — but only when the parent isn't the origin
        # and the user actually came from somewhere.
        back_dir: Optional[Direction] = OPPOSITE.get(req.direction)

        mcp_summary: Optional[str] = None
        if mcp_output is not None:
            mcp_summary = json.dumps(mcp_output, default=str)[:1200]

        forward_intents = await generate_adjacent_intents(
            current_layout=layout,
            current_title=layout.headline,
            history_titles=history_titles,
            back_direction=back_dir,
            back_target_title=parent.title,
            mcp_tool_executed=req.mcp_tool,
            mcp_output_summary=mcp_summary,
        )
        all_intents = list(forward_intents.intents)
        if back_dir:
            all_intents.append(make_back_intent(
                direction=back_dir,
                target_node_id=parent.node_id,
                parent_title=parent.title,
            ))
        from ..schemas import AdjacentIntents as _AI
        intents = _AI(intents=all_intents)
        if key: await _push(key, "✓ intents ready")

        node = db.insert_node(
            session_id=parent.session_id,
            parent_node_id=parent.node_id,
            direction_from_parent=req.direction,
            coord_x=nx,
            coord_y=ny,
            mcp_tool_executed=req.mcp_tool,
            title=layout.headline[:80],
            layout=layout,
            adjacent_intents=intents,
        )
        if key:
            await _push(key, f"✓ node {node.node_id[:8]} materialized")
            await _push(key, "[[DONE]]")
            sent_done = True
        return NavigateResponse(node=node)
    except Exception as e:  # noqa: BLE001
        if key:
            await _push(key, f"✗ navigate failed: {e}")
            await _push(key, "[[DONE]]")
            sent_done = True
        raise
    finally:
        if key and not sent_done:
            await _push(key, "[[DONE]]")
        if key:
            async def _cleanup() -> None:
                await asyncio.sleep(30)
                _streams.pop(key, None)
            asyncio.create_task(_cleanup())
