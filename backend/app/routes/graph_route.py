"""GET /api/graph/{session_id} — full DAG for the archive view."""
from fastapi import APIRouter, HTTPException

from .. import database as db
from ..schemas import GraphResponse

router = APIRouter()


@router.get("/graph/{session_id}", response_model=GraphResponse)
async def graph_endpoint(session_id: str) -> GraphResponse:
    nodes = db.get_session_nodes(session_id)
    if not nodes:
        raise HTTPException(404, "session not found")
    return GraphResponse(session_id=session_id, nodes=nodes)
