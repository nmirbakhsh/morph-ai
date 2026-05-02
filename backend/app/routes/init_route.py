"""POST /api/init — start a session, generate the origin node."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Request

from .. import database as db
from ..llm_engine import generate_adjacent_intents, generate_layout
from ..schemas import InitResponse, NodeRecord

router = APIRouter()


@router.get("/init", response_model=InitResponse)
@router.post("/init", response_model=InitResponse)
async def init_endpoint(request: Request) -> InitResponse:
    cookie_ctx: Dict[str, Any] = {
        "user_agent": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", ""),
    }
    sid = db.create_session(cookie_ctx)

    layout = await generate_layout(
        intent_prompt=(
            "Welcome the user to Morph AI: a spatial canvas where every room is generated "
            "from connected MCP servers. Showcase what they can explore — frame it as a curious "
            "starting point. Pick a warm violet/indigo theme."
        ),
        mcp_tool=None,
        mcp_output=None,
        parent_title=None,
    )
    intents = await generate_adjacent_intents(
        current_layout=layout,
        current_title="Welcome",
        history_titles=[],
        back_direction=None,         # origin — no back
        back_target_title=None,
        mcp_tool_executed=None,
        mcp_output_summary=None,
    )
    node = db.insert_node(
        session_id=sid,
        parent_node_id=None,
        direction_from_parent=None,
        coord_x=0,
        coord_y=0,
        mcp_tool_executed=None,
        title="Welcome",
        layout=layout,
        adjacent_intents=intents,
    )
    return InitResponse(session_id=sid, node=node)
