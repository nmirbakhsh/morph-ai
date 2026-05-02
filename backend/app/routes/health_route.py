"""GET /api/health — liveness + MCP status."""
from fastapi import APIRouter

from ..mcp_client import bridge
from ..tool_registry import master_tool_list

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "mcp_servers": bridge.server_status,
        "tools": master_tool_list(),
    }
