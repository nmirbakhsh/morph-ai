"""GET /api/stream — SSE log stream for an in-flight navigate job."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from ..schemas import Direction
from .navigate_route import _streams, stream_key

router = APIRouter()


@router.get("/stream")
async def stream_endpoint(
    parent_node_id: str = Query(...),
    direction: Direction = Query(...),
) -> EventSourceResponse:
    """Subscribe to log lines for a navigate job keyed by parent + direction."""
    key = stream_key(parent_node_id, direction)

    async def event_gen() -> AsyncIterator[dict]:
        # If the job hasn't started yet, wait briefly for the queue to appear.
        for _ in range(40):
            if key in _streams:
                break
            await asyncio.sleep(0.05)
        q = _streams.get(key)
        if q is None:
            yield {"event": "error", "data": json.dumps({"message": "no stream"})}
            return

        while True:
            try:
                line = await asyncio.wait_for(q.get(), timeout=20.0)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": ""}
                continue
            if line == "[[DONE]]":
                yield {"event": "done", "data": ""}
                return
            yield {"event": "log", "data": line}

    return EventSourceResponse(event_gen())
