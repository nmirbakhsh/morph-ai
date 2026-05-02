"""
MCP client: per-server connections + tool execution.

Uses the official `mcp` Python SDK. Servers listed in config.yaml are spawned
as stdio subprocesses (or connected to via SSE/HTTP) and kept alive for the
lifetime of the FastAPI process.
"""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from .config_loader import MCPServerConfig

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except Exception:  # pragma: no cover - allows backend to boot even if MCP isn't installed yet
    HAS_MCP = False


class MCPBridge:
    """Manages connections to all configured MCP servers."""

    def __init__(self) -> None:
        self._exit_stack: Optional[AsyncExitStack] = None
        self.sessions: Dict[str, "ClientSession"] = {}
        self.server_status: Dict[str, str] = {}  # name -> "connected" | "error: ..."
        # Aggregated tool registry: "<server>:<tool>" -> (server_name, tool_dict)
        self.tools: Dict[str, Tuple[str, Dict[str, Any]]] = {}

    async def connect_all(self, servers: List[MCPServerConfig]) -> None:
        if not HAS_MCP:
            for s in servers:
                self.server_status[s.name] = "error: mcp package not installed"
            return

        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        for srv in servers:
            if not srv.enabled:
                self.server_status[srv.name] = "disabled"
                continue
            try:
                await self._connect_one(srv)
            except Exception as e:  # noqa: BLE001
                self.server_status[srv.name] = f"error: {e}"

    async def _connect_one(self, srv: MCPServerConfig) -> None:
        if srv.transport != "stdio":
            self.server_status[srv.name] = f"error: only stdio supported in this scaffold"
            return
        if not srv.command:
            self.server_status[srv.name] = "error: missing command"
            return

        params = StdioServerParameters(command=srv.command, args=srv.args, env=None)
        read, write = await self._exit_stack.enter_async_context(stdio_client(params))
        session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        self.sessions[srv.name] = session
        self.server_status[srv.name] = "connected"

        listed = await session.list_tools()
        for tool in listed.tools:
            key = f"{srv.name}:{tool.name}"
            self.tools[key] = (srv.name, {
                "name": tool.name,
                "qualified_name": key,
                "server": srv.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema or {},
            })

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t for _, t in self.tools.values()]

    async def call_tool(
        self, qualified_name: str, args: Dict[str, Any] | None = None
    ) -> Any:
        """Call <server>:<tool> with args. Returns raw MCP result content."""
        if qualified_name not in self.tools:
            raise ValueError(f"unknown tool: {qualified_name}")
        server_name, _ = self.tools[qualified_name]
        session = self.sessions.get(server_name)
        if not session:
            raise RuntimeError(f"MCP server '{server_name}' not connected")
        tool_name = qualified_name.split(":", 1)[1]
        result = await session.call_tool(tool_name, args or {})
        return _serialize_result(result)

    async def close(self) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.__aexit__(None, None, None)
            self._exit_stack = None
        self.sessions.clear()


def _serialize_result(result: Any) -> Dict[str, Any]:
    """Flatten MCP CallToolResult into JSON-serializable dict."""
    out: Dict[str, Any] = {"isError": getattr(result, "isError", False), "content": []}
    for c in getattr(result, "content", []) or []:
        # mcp.types.TextContent / ImageContent / EmbeddedResource
        item: Dict[str, Any] = {"type": getattr(c, "type", "unknown")}
        for attr in ("text", "data", "mimeType", "uri"):
            v = getattr(c, attr, None)
            if v is not None:
                item[attr] = v
        out["content"].append(item)
    return out


# Singleton bridge for the FastAPI app
bridge = MCPBridge()


# ─── Stream helpers ──────────────────────────────────────────────────────

async def stream_log_lines(lines: List[str]) -> AsyncIterator[str]:
    """Yield log lines with small delays (cinematic terminal effect)."""
    for line in lines:
        yield line
        await asyncio.sleep(0.08)
