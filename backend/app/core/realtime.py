"""Real-time WebSocket fan-out.

Bridges synchronous code (our `def` routes and the background escalation thread)
to async WebSocket sends on the main event loop. Sync callers use `publish(...)`,
which schedules the send on the captured loop via `run_coroutine_threadsafe` —
safe to call from any thread. Always publish AFTER the DB commit, so a client
that refetches on the event sees committed data.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from starlette.websockets import WebSocket

logger = logging.getLogger("consulthub.realtime")


class ConnectionManager:
    def __init__(self) -> None:
        self._active: dict[int, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._active.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        conns = self._active.get(user_id)
        if conns is not None:
            conns.discard(ws)
            if not conns:
                self._active.pop(user_id, None)

    async def _send(self, user_ids: list[int], event: dict[str, Any]) -> None:
        for uid in user_ids:
            for ws in list(self._active.get(uid, ())):
                try:
                    await ws.send_json(event)
                except Exception:
                    self.disconnect(uid, ws)

    def publish(
        self, user_ids: Iterable[int], event: dict[str, Any]
    ) -> None:
        """Thread-safe: schedule the send on the main event loop."""
        ids = [u for u in dict.fromkeys(user_ids) if u is not None]
        if not ids or self._loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._send(ids, event), self._loop
            )
        except Exception:
            logger.exception("Failed to schedule realtime publish")


manager = ConnectionManager()
