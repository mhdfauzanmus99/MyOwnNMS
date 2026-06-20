"""Server-Sent Events stream for real-time alerts/notifications.

Uses EventSource on the client. Note SSE must run on the main thread, and our
publisher is called from poller threads, so events.py bridges via call_soon_threadsafe.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .. import events
from ..auth import require_user

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/stream")
async def stream(request: Request, _user=Depends(require_user)) -> StreamingResponse:
    q = await events.subscribe()

    async def event_gen():
        try:
            # Initial hello so the client knows the stream is live.
            yield f"data: {json.dumps({'kind': 'hello', 'ts': None})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive comment prevents proxy/browser idle drops.
                    yield ": keep-alive\n\n"
        finally:
            await events.unsubscribe(q)

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })
