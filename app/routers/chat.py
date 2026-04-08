"""
Chat endpoint — SSE streaming.

POST /agents/{agent_id}/chat
Response: text/event-stream

SSE event format:
    data: {"type": "token", "content": "..."}
    data: {"type": "tool_start", "tool_call_id": "...", "name": "...", "input": {...}}
    data: {"type": "tool_end", "tool_call_id": "...", "output": <JSON-serializable>}
    data: {"type": "done"}
    data: {"type": "error", "message": "..."}
"""
import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session, session_scope
from app.db.queries import agents as agents_q
from app.db.queries import sessions as sessions_q
from app.llm.engine.agent_engine import AgentEngine
from app.models.chat import ChatRequest
from app.models.session import SessionEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["chat"])


@router.post("/{agent_id}/chat/image")
async def upload_chat_image(
    agent_id: uuid.UUID,
    user_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
):
    """Upload an image for use as vision input in chat. Returns a public URL."""
    from app.storage import upload_file, get_public_url, BUCKET

    data = await file.read()
    mime_type = file.content_type or "image/jpeg"
    ext = mime_type.split("/")[-1].split(";")[0]  # strip params e.g. "jpeg; charset=..."
    storage_path = f"{user_id}/chat-images/{uuid.uuid4()}.{ext}"

    try:
        await upload_file(BUCKET, storage_path, data, mime_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    public_url = get_public_url(BUCKET, storage_path)
    return {"public_url": public_url}


@router.post("/{agent_id}/chat")
async def chat(
    agent_id: uuid.UUID,
    body: ChatRequest,
    db_session: AsyncSession = Depends(get_session),
):
    t_start = time.perf_counter()

    agent = await agents_q.get_agent(db_session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Ensure session row exists before streaming starts.
    await sessions_q.upsert_session(db_session, body.session_id, agent_id, body.user_id)

    # Record the user's message.
    await sessions_q.append_event(
        db_session,
        body.session_id,
        event_type=SessionEventType.user_message,
        event_body=body.message,
    )
    logger.info(
        "User message agent_id=%s session_id=%s: %s",
        agent_id,
        body.session_id,
        body.message[:200],
    )

    engine = AgentEngine(agent_id, body.user_id, body.session_id, db_session)
    await engine.setup(agent)

    logger.info(
        "chat_setup agent_id=%s session_id=%s setup_ms=%.0f",
        agent_id,
        body.session_id,
        (time.perf_counter() - t_start) * 1000,
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        ai_tokens: list[str] = []

        try:
            async for event in engine.astream(body.message, images=body.images):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if isinstance(content, str):
                        frag = content
                    elif isinstance(content, list):
                        frag = "".join(
                            b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    else:
                        frag = ""
                    if frag:
                        ai_tokens.append(frag)
                        yield f"data: {json.dumps({'type': 'token', 'content': frag}, default=str)}\n\n"

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    d = event["data"]
                    raw = d.get("input")
                    tool_input = raw if isinstance(raw, dict) else {}
                    tool_call_id = str(d.get("tool_call_id") or event.get("run_id") or "").strip()

                    async with session_scope() as s:
                        await sessions_q.append_event(
                            s,
                            body.session_id,
                            event_type=SessionEventType.tool_start,
                            event_title=tool_name,
                            event_body=json.dumps(tool_input, default=str),
                        )
                    logger.info(
                        "Tool call agent_id=%s session_id=%s name=%s tool_call_id=%s input=%s",
                        agent_id,
                        body.session_id,
                        tool_name,
                        tool_call_id,
                        json.dumps(tool_input, default=str)[:200],
                    )
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "tool_start",
                                "tool_call_id": tool_call_id,
                                "name": tool_name,
                                "input": tool_input,
                            },
                            default=str,
                        )
                        + "\n\n"
                    )

                elif kind == "on_tool_end":
                    d = event["data"]
                    tool_output = d.get("output", "")
                    out_str = str(tool_output)
                    try:
                        out_sse = json.loads(json.dumps(tool_output, default=str))
                    except (TypeError, ValueError):
                        out_sse = str(tool_output)
                    tool_call_id = str(d.get("tool_call_id") or event.get("run_id") or "").strip()
                    async with session_scope() as s:
                        await sessions_q.append_event(
                            s,
                            body.session_id,
                            event_type=SessionEventType.tool_end,
                            event_title=event["name"],
                            event_body=out_str,
                        )
                    logger.info(
                        "Tool response agent_id=%s session_id=%s name=%s tool_call_id=%s output=%s",
                        agent_id,
                        body.session_id,
                        event["name"],
                        tool_call_id,
                        out_str[:200],
                    )
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "tool_end",
                                "tool_call_id": tool_call_id,
                                "output": out_sse,
                            },
                            default=str,
                        )
                        + "\n\n"
                    )

                elif kind == "on_tool_error":
                    d = event["data"]
                    tool_call_id = str(d.get("tool_call_id") or event.get("run_id") or "").strip()
                    err = d.get("error")
                    err_str = str(err) if err is not None else "tool_error"
                    async with session_scope() as s:
                        await sessions_q.append_event(
                            s,
                            body.session_id,
                            event_type=SessionEventType.tool_end,
                            event_title=event["name"],
                            event_body=err_str,
                        )
                    logger.warning(
                        "Tool error agent_id=%s session_id=%s name=%s tool_call_id=%s %s",
                        agent_id,
                        body.session_id,
                        event["name"],
                        tool_call_id,
                        err_str[:500],
                    )
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "tool_end",
                                "tool_call_id": tool_call_id,
                                "output": {"error": err_str},
                            },
                            default=str,
                        )
                        + "\n\n"
                    )

            # Persist the complete AI reply after streaming finishes.
            reply_text = "".join(ai_tokens)
            logger.info(
                "AI reply agent_id=%s session_id=%s (%d chars): %s",
                agent_id,
                body.session_id,
                len(reply_text),
                reply_text[:400],
            )
            if reply_text:
                async with session_scope() as s:
                    await sessions_q.append_event(
                        s,
                        body.session_id,
                        event_type=SessionEventType.ai_message,
                        event_body=reply_text,
                    )

            yield f"data: {json.dumps({'type': 'done'}, default=str)}\n\n"

        except Exception as e:
            logger.exception(
                "Chat stream failed agent_id=%s session_id=%s",
                agent_id,
                body.session_id,
            )
            async with session_scope() as s:
                await sessions_q.append_event(
                    s,
                    body.session_id,
                    event_type=SessionEventType.error,
                    event_body=str(e),
                )
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, default=str)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
