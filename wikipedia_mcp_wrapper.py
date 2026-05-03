"""
Launches the upstream `wikipedia-mcp-server` after monkey-patching
httpx.AsyncClient to send a real User-Agent. Wikipedia returns 403 for
clients with no UA per their API policy.

Run with the backend's venv python so wikipedia_mcp is available:

    /root/morph-ai/backend/venv/bin/python wikipedia_mcp_wrapper.py
"""
from __future__ import annotations

import httpx

_UA = "MorphAI-WikipediaBridge/0.2 (+https://github.com/nmirbakhsh/morph-ai)"

_OriginalAsyncClient = httpx.AsyncClient


class _PatchedAsyncClient(_OriginalAsyncClient):
    def __init__(self, *args, **kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("User-Agent", _UA)
        kwargs["headers"] = headers
        super().__init__(*args, **kwargs)


httpx.AsyncClient = _PatchedAsyncClient

# Now import the MCP server — its module-level AsyncClient construction will
# pick up our patched class.
from wikipedia_mcp.server import mcp  # noqa: E402


if __name__ == "__main__":
    mcp.run()
