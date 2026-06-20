"""Server-Sent Events broadcaster.

A tiny in-process pub/sub: the poller/alerts code publishes events, and each
connected SSE client has its own asyncio Queue fed by a single background task
that drains a thread-safe buffer.

Kept intentionally simple — fine for a handful of dashboard tabs open at once.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_subscribers: set[asyncio.Queue] = set()
_lock = asyncio.Lock()


async def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    async with _lock:
        _subscribers.add(q)
    return q


async def unsubscribe(q: asyncio.Queue) -> None:
    async with _lock:
        _subscribers.discard(q)


def publish(event: dict[str, Any]) -> None:
    """Thread-safe publish: schedules the fan-out on the running event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Called from a poller thread with no running loop in *this* thread —
        # grab the one uvicorn started (set by main.py at startup).
        loop = _main_loop
        if loop is None:
            return
    loop.call_soon_threadsafe(asyncio.create_task, _fanout(event))


_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


async def _fanout(event: dict[str, Any]) -> None:
    payload = json.dumps(event, default=str)
    dead: list[asyncio.Queue] = []
    async with _lock:
        subs = list(_subscribers)
    for q in subs:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            # Slow client — drop oldest then push latest so it stays live.
            try:
                q.get_nowait()
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
    if dead:
        async with _lock:
            for q in dead:
                _subscribers.discard(q)
