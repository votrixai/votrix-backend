"""
Notification connection manager.

Maintains a registry of active WebSocket connections keyed by user_id.
When a cron job completes, the scheduler calls `push()` to deliver
the notification to any connected clients for that user in real-time.

Usage:
    # In WS endpoint:
    await notification_manager.connect(user_id, websocket)
    try:
        await notification_manager.wait(websocket)   # keep alive
    finally:
        notification_manager.disconnect(user_id, websocket)

    # In scheduler runner after job completes:
    await notification_manager.push(user_id, payload_dict)
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Any, Dict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self) -> None:
        # user_id → set of active WebSocket connections
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)
        logger.debug("Notification WS connected user=%s total=%d", user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            del self._connections[user_id]
        logger.debug("Notification WS disconnected user=%s", user_id)

    async def push(self, user_id: uuid.UUID, payload: Dict[str, Any]) -> None:
        """Send a notification to all active connections for user_id."""
        connections = list(self._connections.get(user_id, []))
        if not connections:
            return

        text = json.dumps(payload, default=str)
        results = await asyncio.gather(
            *(ws.send_text(text) for ws in connections),
            return_exceptions=True,
        )
        for ws, result in zip(connections, results):
            if isinstance(result, Exception):
                logger.warning("Failed to push notification to user=%s: %s", user_id, result)
                self.disconnect(user_id, ws)

    async def wait(self, websocket: WebSocket) -> None:
        """
        Keep the connection alive, handling pings and disconnects.
        Exits when the client disconnects.
        """
        from fastapi.websockets import WebSocketDisconnect
        try:
            while True:
                data = await websocket.receive_text()
                # Support client-side ping to keep the connection alive
                if data.strip() == '{"type":"ping"}':
                    await websocket.send_text('{"type":"pong"}')
        except WebSocketDisconnect:
            pass


# Module-level singleton shared across the app
notification_manager = NotificationManager()
