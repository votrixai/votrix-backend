import uuid

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.ws.handler import WSHandler

router = APIRouter(prefix="/agents", tags=["chat-ws"])


@router.websocket("/{agent_id}/ws")
async def chat_websocket(
    agent_id: uuid.UUID,
    websocket: WebSocket,
    db_session: AsyncSession = Depends(get_session),
):
    """
    WS /agents/{agent_id}/ws?user_id={uuid}&session_id={uuid}

    Protocol (JSON text frames):
        client → server : {"message": "..."}
        server → client : {"type": "token"|"tool_start"|"tool_end"|"done"|"error", ...}
    """
    user_id = uuid.UUID(websocket.query_params["user_id"])
    session_id = uuid.UUID(websocket.query_params["session_id"])

    await websocket.accept()

    handler = WSHandler(websocket, agent_id, user_id, session_id, db_session)
    await handler.setup()
    await handler.run()
