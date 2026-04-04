"""Regression: ShortIdMiddleware + JSON POST + StreamingResponse must not break ASGI.

Replacing ``request._receive`` with a receive that always returns ``http.request``
caused after-response errors:

    RuntimeError: Unexpected message received: http.request

when BaseHTTPMiddleware forwarded disconnect listening to ``request._receive``.
"""

import uuid

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.testclient import TestClient

from app.short_id import ShortIdMiddleware


def _mini_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ShortIdMiddleware)

    @app.post("/sse")
    async def sse():
        async def gen():
            yield 'data: {"type":"ping"}\n\n'

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def test_json_post_with_short_id_middleware_streaming_response_completes():
    app = _mini_app()
    uid = str(uuid.uuid4())
    sid = str(uuid.uuid4())
    with TestClient(app) as client:
        r = client.post(
            "/sse",
            json={"user_id": uid, "session_id": sid, "message": "hi"},
            headers={"Accept": "text/event-stream"},
        )
    assert r.status_code == 200
    assert "ping" in r.text
