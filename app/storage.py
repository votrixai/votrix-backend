"""Supabase Storage client for image uploads."""

from __future__ import annotations

import uuid
from functools import lru_cache

from supabase import create_client, Client

from app.config import get_settings

BUCKET = "public-files"


@lru_cache
def _get_client() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_key)


def upload_image(data: bytes, mime_type: str, user_id: str) -> str:
    """Upload image bytes to Supabase Storage. Returns public URL."""
    ext = mime_type.split("/")[-1]
    path = f"{user_id}/images/{uuid.uuid4()}.{ext}"
    client = _get_client()
    client.storage.from_(BUCKET).upload(path, data, {"content-type": mime_type, "upsert": "true"})
    return client.storage.from_(BUCKET).get_public_url(path)
