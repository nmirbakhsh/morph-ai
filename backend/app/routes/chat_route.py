"""POST /api/chat — natural-language router (teleport or explain)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..llm_engine import (
    chat_route, generate_adjacent_intents, generate_layout, make_back_intent,
)
from ..schemas import AdjacentIntents, ChatRequest, ChatResponse

router = APIRouter()


def _summarize(layout) -> str:
    parts = [layout.eyebrow, layout.headline]
    if layout.body:
        parts.append(layout.body)
    return " · ".join(parts)[:300]


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    current = db.get_node(req.current_node_id)
    if not current:
        raise HTTPException(404, "current node not found")

    mode, reply, teleport_intent, followups = await chat_route(
        message=req.message,
        current_title=current.title,
        current_layout_summary=_summarize(current.layout),
    )

    teleport_node = None
    if mode == "teleport" and teleport_intent:
        # Teleport: spawn a new node parented to current, but at a fresh coord.
        # Find an unused coord by stepping diagonally outward until free.
        x, y = current.coord_x, current.coord_y
        for step in range(1, 50):
            cand = (x + step, y + step)
            if not db.find_node_at_coord(req.session_id, *cand):
                x, y = cand
                break

        layout = await generate_layout(
            intent_prompt=teleport_intent,
            mcp_tool=None,
            mcp_output=None,
            parent_title=current.title,
        )
        history_titles = [n.title for n in db.get_session_nodes(req.session_id)]
        # Teleport has no spatial parent direction — give the user a Back
        # signpost on "left" (an arbitrary but consistent slot).
        back_dir = "left"
        forward = await generate_adjacent_intents(
            current_layout=layout,
            current_title=layout.headline,
            history_titles=history_titles,
            back_direction=back_dir,
            back_target_title=current.title,
            mcp_tool_executed=None,
            mcp_output_summary=None,
        )
        all_intents = list(forward.intents)
        all_intents.append(make_back_intent(
            direction=back_dir,
            target_node_id=current.node_id,
            parent_title=current.title,
        ))
        intents = AdjacentIntents(intents=all_intents)
        teleport_node = db.insert_node(
            session_id=req.session_id,
            parent_node_id=current.node_id,
            direction_from_parent=None,  # teleport has no direction
            coord_x=x,
            coord_y=y,
            mcp_tool_executed=None,
            title=layout.headline[:80],
            layout=layout,
            adjacent_intents=intents,
        )

    return ChatResponse(reply=reply, teleport_node=teleport_node, followups=followups)
