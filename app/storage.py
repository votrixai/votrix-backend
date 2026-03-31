"""Supabase Storage client for binary file uploads/downloads."""

from __future__ import annotations

from functools import lru_cache

from supabase import create_client, Client

from app.config import get_settings

BUCKET = "files"

# MIME types treated as text (stored inline in Postgres)
_TEXT_PREFIXES = ("text/",)
_TEXT_EXACT = {
    "application/json",
    "application/yaml",
    "application/x-yaml",
    "application/xml",
    "application/javascript",
    "application/typescript",
    "application/x-sh",
    "application/sql",
    "application/graphql",
    "application/toml",
    "application/x-toml",
}


def is_text_mime(mime_type: str) -> bool:
    """Return True if the MIME type should be stored as text in Postgres."""
    mime = mime_type.lower().split(";")[0].strip()
    if any(mime.startswith(p) for p in _TEXT_PREFIXES):
        return True
    return mime in _TEXT_EXACT


@lru_cache
def _get_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


async def upload_file(bucket: str, path: str, data: bytes, mime_type: str) -> str:
    """Upload binary data to Supabase Storage. Returns the storage path."""
    client = _get_client()
    client.storage.from_(bucket).upload(
        path, data, {"content-type": mime_type, "upsert": "true"}
    )
    return path


async def download_file(bucket: str, path: str) -> bytes:
    """Download binary data from Supabase Storage."""
    client = _get_client()
    return client.storage.from_(bucket).download(path)


async def delete_file(bucket: str, path: str) -> None:
    """Delete a file from Supabase Storage."""
    client = _get_client()
    client.storage.from_(bucket).remove([path])


async def copy_file(bucket: str, src_path: str, dst_path: str, mime_type: str = "application/octet-stream") -> str:
    """Copy a file within Supabase Storage by downloading and re-uploading."""
    data = await download_file(bucket, src_path)
    await upload_file(bucket, dst_path, data, mime_type)
    return dst_path


def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """Generate a signed download URL for a storage file."""
    client = _get_client()
    res = client.storage.from_(bucket).create_signed_url(path, expires_in)
    return res["signedURL"]
