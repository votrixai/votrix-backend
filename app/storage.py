"""Supabase Storage — direct REST API via httpx (no supabase-py client)."""

from __future__ import annotations

import asyncio
import uuid

import httpx

from app.config import get_settings

BUCKET = "public-files"

_http: httpx.AsyncClient | None = None
_lock = asyncio.Lock()


async def _client() -> httpx.AsyncClient:
    global _http
    async with _lock:
        if _http is None:
            s = get_settings()
            _http = httpx.AsyncClient(
                base_url=f"{s.supabase_url}/storage/v1",
                headers={"apikey": s.supabase_service_key, "Authorization": f"Bearer {s.supabase_service_key}"},
                timeout=30,
            )
    return _http


async def upload_image(data: bytes, mime_type: str, user_id: str) -> str:
    """Upload image bytes to Supabase Storage. Returns public URL."""
    ext = mime_type.split("/")[-1]
    path = f"{user_id}/images/{uuid.uuid4()}.{ext}"
    http = await _client()
    s = get_settings()
    resp = await http.post(
        f"/object/{BUCKET}/{path}",
        content=data,
        headers={"Content-Type": mime_type, "x-upsert": "true"},
    )
    resp.raise_for_status()
    return f"{s.supabase_url}/storage/v1/object/public/{BUCKET}/{path}"
