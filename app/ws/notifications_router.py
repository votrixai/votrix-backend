"""WebSocket endpoint for real-time notification push.

WS /users/{user_id}/notifications/ws

Client connects once per user session and receives notification events
whenever a cron job (or any background task) completes.

Protocol (JSON text frames):
    server → client : {
        "type": "notification",
        "id":   "<uuid>",
        "title": "...",
        "body":  "...",
        "notification_type": "cron_content" | "cron_review" | "cron_analytics",
        "metadata": { "session_id": "...", "job_id": "...", ... },
        "created_at": "<iso8601>"
    }
    client → server : {"type": "ping"}
    server → client : {"type": "pong"}
"""

import uuid

from fastapi import APIRouter, WebSocket

from app.notifications.manager import notification_manager

router = APIRouter(prefix="/users", tags=["notifications-ws"])


@router.websocket("/{user_id}/notifications/ws")
async def notifications_websocket(user_id: uuid.UUID, websocket: WebSocket):
    await notification_manager.connect(user_id, websocket)
    try:
        await notification_manager.wait(websocket)
    finally:
        notification_manager.disconnect(user_id, websocket)
