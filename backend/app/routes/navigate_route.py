"""POST /api/navigate — generate the room in a chosen direction."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..llm_engine import (
    OPPOSITE, generate_full_node, make_back_intent, synthesize_mcp_args,
)
from ..mcp_client import bridge
from ..schemas import AdjacentIntents, Direction, NavigateRequest, NavigateResponse

router = APIRouter()


_DIR_DELTAS: Dict[str, tuple[int, int]] = {
    "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
}


import re

import logging
_log = logging.getLogger("morph.chain")


async def _maybe_chain_fetch(
    *, tool_name: Optional[str], first_output: Optional[Dict[str, Any]],
    stream_key: Optional[str],
) -> Optional[Dict[str, Any]]:
    """If the first call was wikipedia:search and returned page ids, fetch the
    top result so its HTML (with <img> tags) feeds Prompt B."""
    if not first_output or tool_name != "wikipedia:search":
        return first_output
    if first_output.get("isError"):
        _log.info("chain skip: first_output isError")
        return first_output
    # MCP wraps the search result as a JSON-string inside content[0].text.
    page_id: Optional[int] = None
    for item in first_output.get("content", []) or []:
        if not isinstance(item, dict) or item.get("type") != "text":
            continue
        text = item.get("text") or ""
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        seq = data if isinstance(data, list) else [data]
        for entry in seq:
            if isinstance(entry, dict) and "id" in entry:
                try:
                    page_id = int(entry["id"])
                    break
                except (TypeError, ValueError):
                    pass
        if page_id is not None:
            break
    if page_id is None:
        _log.info("chain skip: no page id in search result")
        return first_output
    _log.info("chain: fetching page id %s", page_id)
    try:
        if stream_key:
            await _push(stream_key, f"▶ fetching page id {page_id} for richer content")
        # Wikipedia MCP fetch requires both id AND language (no default).
        fetched = await bridge.call_tool(
            "wikipedia:fetch", {"id": page_id, "language": "en"},
        )
        merged = {
            "isError": False,
            "content": list(first_output.get("content", []))
                       + list((fetched or {}).get("content", [])),
        }
        merged_len = sum(len(json.dumps(c)) for c in merged["content"])
        _log.info("chain: merged content size %d (was %d)", merged_len,
                  len(json.dumps(first_output.get("content", []))))
        if stream_key: await _push(stream_key, "✓ fetched")
        return merged
    except Exception as e:  # noqa: BLE001
        _log.warning("chain fetch failed: %s", e)
        if stream_key: await _push(stream_key, f"✗ fetch chain failed: {e}")
        return first_output


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

            # Image enrichment: when search returned results that include a
            # page id, also fetch the page so HTML <img> tags become available
            # to Prompt B. Wikipedia-specific helper, no-op otherwise.
            mcp_output = await _maybe_chain_fetch(
                tool_name=req.mcp_tool,
                first_output=mcp_output,
                stream_key=key,
            )

        if key: await _push(key, "▶ generating room + next intents (merged)…")
        history_titles = [n.title for n in db.get_session_nodes(parent.session_id)]
        back_dir: Optional[Direction] = OPPOSITE.get(req.direction)

        # Sticky continue: if the parent's intent in this direction was a
        # continuation, keep continuations on the same direction here too.
        parent_intent = next(
            (i for i in parent.adjacent_intents.intents if i.direction == req.direction),
            None,
        )
        prefer_cont_dir: Optional[Direction] = (
            req.direction if (parent_intent and parent_intent.is_continuation) else None
        )

        layout, forward_intents = await generate_full_node(
            intent_prompt=req.intent_prompt,
            mcp_tool=req.mcp_tool,
            mcp_output=mcp_output,
            parent_title=parent.title,
            history_titles=history_titles,
            back_direction=back_dir,
            viewport_w=req.viewport_w,
            viewport_h=req.viewport_h,
            prefer_continuation_direction=prefer_cont_dir,
            prefs=req.prefs,
        )
        if key: await _push(key, "✓ layout + intents ready")

        all_intents = list(forward_intents.intents)
        if back_dir:
            all_intents.append(make_back_intent(
                direction=back_dir,
                target_node_id=parent.node_id,
                parent_title=parent.title,
            ))
        intents = AdjacentIntents(intents=all_intents)

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
