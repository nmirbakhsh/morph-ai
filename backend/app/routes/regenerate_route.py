"""POST /api/regenerate — refresh an existing node with new prefs / viewport.

Reuses the original intent prompt by walking back to the parent node's
adjacent intents (or, for the origin, falls back to the welcome prompt).
The node id and coord are preserved so the user's spatial position on
the canvas doesn't shift.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..llm_engine import OPPOSITE, generate_full_node, make_back_intent
from ..schemas import (
    AdjacentIntents, RegenerateRequest, RegenerateResponse,
)

router = APIRouter()


_WELCOME_PROMPT = (
    "Welcome the user to Morph AI: a spatial canvas where every room is "
    "generated from connected MCP servers. Showcase what they can explore "
    "— frame it as a curious starting point. Pick a warm violet/indigo theme."
)


@router.post("/regenerate", response_model=RegenerateResponse)
async def regenerate_endpoint(req: RegenerateRequest) -> RegenerateResponse:
    node = db.get_node(req.node_id)
    if not node:
        raise HTTPException(404, "node not found")

    intent_prompt = _WELCOME_PROMPT
    mcp_tool = None
    parent_title = None
    back_dir = None
    if node.parent_node_id:
        parent = db.get_node(node.parent_node_id)
        if parent:
            parent_title = parent.title
            if node.direction_from_parent:
                parent_intent = next(
                    (i for i in parent.adjacent_intents.intents
                     if i.direction == node.direction_from_parent),
                    None,
                )
                if parent_intent:
                    intent_prompt = parent_intent.intent_prompt
                    mcp_tool = parent_intent.mcp_tool
                back_dir = OPPOSITE.get(node.direction_from_parent)

    history_titles = [n.title for n in db.get_session_nodes(node.session_id)]

    layout, forward = await generate_full_node(
        intent_prompt=intent_prompt,
        mcp_tool=mcp_tool,
        mcp_output=None,
        parent_title=parent_title,
        history_titles=history_titles,
        back_direction=back_dir,
        viewport_w=req.viewport_w,
        viewport_h=req.viewport_h,
        prefs=req.prefs,
    )

    all_intents = list(forward.intents)
    if back_dir and node.parent_node_id:
        all_intents.append(make_back_intent(
            direction=back_dir,
            target_node_id=node.parent_node_id,
            parent_title=parent_title or "Previous room",
        ))
    intents = AdjacentIntents(intents=all_intents)

    updated = db.update_node_layout(
        node_id=node.node_id,
        title=layout.headline[:80],
        layout=layout,
        adjacent_intents=intents,
    )
    if not updated:
        raise HTTPException(500, "node update failed")
    return RegenerateResponse(node=updated)
