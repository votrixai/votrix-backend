"""Unit tests for the image_upload platform tool handler.

Tests verify:
- base64 decoding and forwarding to Supabase Storage
- public permanent URL is returned (get_public_url, not signed URL)
- full_path is correctly namespaced under the user_id
- invalid base64 returns a clean error without hitting storage
- upload failures are surfaced correctly
"""

import base64
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.handlers.platform import FileContext, _make_image_upload_handler


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx():
    return FileContext(
        session=AsyncMock(),
        blueprint_agent_id=uuid.uuid4(),
        user_id=uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"),
    )


PNG_1PX = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
).decode()


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_returns_public_url(ctx):
    """Handler must call get_public_url and return it as public_url."""
    handler = _make_image_upload_handler(ctx)

    with (
        patch("app.storage.upload_file", new_callable=AsyncMock) as mock_upload,
        patch("app.storage.get_public_url", return_value="https://cdn.example.com/img.png") as mock_pub,
    ):
        result = await handler(PNG_1PX, "images/test.png")

    assert result["status"] is True
    assert result["public_url"] == "https://cdn.example.com/img.png"
    mock_pub.assert_called_once()


@pytest.mark.asyncio
async def test_storage_path_namespaced_under_user_id(ctx):
    """full_path must be '{user_id}/{storage_path}' with no double slashes."""
    handler = _make_image_upload_handler(ctx)
    captured = {}

    async def fake_upload(bucket, path, data, mime_type):
        captured["path"] = path
        return path

    with (
        patch("app.storage.upload_file", side_effect=fake_upload),
        patch("app.storage.get_public_url", return_value="https://x.com/img.png"),
    ):
        result = await handler(PNG_1PX, "/images/test.png")

    expected = f"{ctx.user_id}/images/test.png"
    assert captured["path"] == expected
    assert result["storage_path"] == expected


@pytest.mark.asyncio
async def test_storage_path_strips_leading_slash(ctx):
    """Leading slash on storage_path must be stripped (no double-slash in Supabase key)."""
    handler = _make_image_upload_handler(ctx)
    captured = {}

    async def fake_upload(bucket, path, data, mime_type):
        captured["path"] = path

    with (
        patch("app.storage.upload_file", side_effect=fake_upload),
        patch("app.storage.get_public_url", return_value="https://x.com/img.png"),
    ):
        await handler(PNG_1PX, "///deep/nested/img.png")

    assert "//" not in captured["path"]
    assert captured["path"].startswith(str(ctx.user_id))


@pytest.mark.asyncio
async def test_raw_bytes_forwarded_to_upload(ctx):
    """Decoded bytes must be forwarded to upload_file unchanged."""
    handler = _make_image_upload_handler(ctx)
    raw = b"\x00\x01\x02\x03"
    b64 = base64.b64encode(raw).decode()
    captured = {}

    async def fake_upload(bucket, path, data, mime_type):
        captured["data"] = data

    with (
        patch("app.storage.upload_file", side_effect=fake_upload),
        patch("app.storage.get_public_url", return_value="https://x.com/img.png"),
    ):
        await handler(b64, "img.bin", mime_type="application/octet-stream")

    assert captured["data"] == raw


@pytest.mark.asyncio
async def test_mime_type_forwarded(ctx):
    """mime_type parameter must be forwarded to upload_file."""
    handler = _make_image_upload_handler(ctx)
    captured = {}

    async def fake_upload(bucket, path, data, mime_type):
        captured["mime_type"] = mime_type

    with (
        patch("app.storage.upload_file", side_effect=fake_upload),
        patch("app.storage.get_public_url", return_value="https://x.com/img.png"),
    ):
        await handler(PNG_1PX, "img.jpg", mime_type="image/jpeg")

    assert captured["mime_type"] == "image/jpeg"


# ── Error paths ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_base64_returns_error_without_upload(ctx):
    """Invalid base64 must short-circuit before touching storage."""
    handler = _make_image_upload_handler(ctx)

    with patch("app.storage.upload_file", new_callable=AsyncMock) as mock_upload:
        result = await handler("!!!not-valid-base64!!!", "img.png")

    assert result["status"] is False
    assert "base64" in result["message"].lower() or "invalid" in result["message"].lower()
    mock_upload.assert_not_called()


@pytest.mark.asyncio
async def test_upload_failure_returned_as_error(ctx):
    """Storage upload errors must be caught and returned cleanly."""
    handler = _make_image_upload_handler(ctx)

    async def boom(bucket, path, data, mime_type):
        raise RuntimeError("Supabase unreachable")

    with (
        patch("app.storage.upload_file", side_effect=boom),
        patch("app.storage.get_public_url") as mock_pub,
    ):
        result = await handler(PNG_1PX, "img.png")

    assert result["status"] is False
    assert "Supabase unreachable" in result["message"]
    mock_pub.assert_not_called()
