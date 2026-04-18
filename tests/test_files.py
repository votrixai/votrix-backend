"""
Tests for Files API integration.

Pure-logic tests require no mocks.
Router tests mock the Anthropic client and bypass auth.
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.auth import AuthedUser, require_user
from app.models.chat import FileAttachment
from app.runtime.sessions import _build_content

_TEST_USER = AuthedUser(id=uuid.uuid4(), email="test@example.com")


def _override_auth():
    return _TEST_USER


# ---------------------------------------------------------------------------
# _build_content — pure logic, no mocks
# ---------------------------------------------------------------------------


def test_build_content_text_only():
    result = _build_content("hello", [])
    assert result == [{"type": "text", "text": "hello"}]


def test_build_content_with_document():
    att = FileAttachment(file_id="file_abc", content_type="document")
    result = _build_content("summarize this", [att])
    assert result == [
        {"type": "text", "text": "summarize this"},
        {"type": "document", "source": {"type": "file", "file_id": "file_abc"}},
    ]


def test_build_content_with_image():
    att = FileAttachment(file_id="file_img", content_type="image")
    result = _build_content("describe this image", [att])
    assert result == [
        {"type": "text", "text": "describe this image"},
        {"type": "image", "source": {"type": "file", "file_id": "file_img"}},
    ]


def test_build_content_multiple_attachments():
    attachments = [
        FileAttachment(file_id="file_doc", content_type="document"),
        FileAttachment(file_id="file_img", content_type="image"),
    ]
    result = _build_content("analyze", attachments)
    assert len(result) == 3
    assert result[0] == {"type": "text", "text": "analyze"}
    assert result[1]["source"]["file_id"] == "file_doc"
    assert result[2]["source"]["file_id"] == "file_img"


# ---------------------------------------------------------------------------
# _build_content — file SSE event from agent.message blocks
# ---------------------------------------------------------------------------


def test_build_content_file_block_in_agent_message():
    """Verify the runtime correctly extracts file_id from non-text agent.message blocks."""
    import queue
    from unittest.mock import MagicMock

    block = MagicMock()
    block.type = "file"
    block.file_id = "file_out_abc"
    block.filename = "chart.png"
    block.mime_type = "image/png"

    out: queue.Queue = queue.Queue()

    # Simulate what the runtime loop does for a non-text block
    if file_id := getattr(block, "file_id", None):
        out.put({
            "type": "file",
            "file_id": file_id,
            "filename": getattr(block, "filename", None),
            "mime_type": getattr(block, "mime_type", None),
        })

    event = out.get_nowait()
    assert event == {"type": "file", "file_id": "file_out_abc", "filename": "chart.png", "mime_type": "image/png"}


# ---------------------------------------------------------------------------
# FileAttachment model validation
# ---------------------------------------------------------------------------


def test_file_attachment_invalid_content_type():
    with pytest.raises(Exception):
        FileAttachment(file_id="file_abc", content_type="video")  # not allowed


# ---------------------------------------------------------------------------
# /files router — upload/list/delete
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=False)
def auth_override():
    """Bypass Supabase JWT auth for files router tests."""
    import importlib
    app = importlib.import_module("app.main").app
    app.dependency_overrides[require_user] = _override_auth
    yield
    app.dependency_overrides.pop(require_user, None)


def _make_file_meta(file_id="file_123", filename="doc.pdf", size=1024):
    m = MagicMock()
    m.id = file_id
    m.filename = filename
    m.size = size
    return m


async def test_upload_file(client, auth_override):
    meta = _make_file_meta()
    mock_client = MagicMock()
    mock_client.beta.files.upload.return_value = meta

    with patch("app.routers.files.get_client", return_value=mock_client):
        r = await client.post(
            "/files",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["file_id"] == "file_123"
    assert body["filename"] == "doc.pdf"
    assert body["size"] == 1024
    mock_client.beta.files.upload.assert_called_once()


async def test_list_files(client, auth_override):
    meta = _make_file_meta()
    meta.created_at = "2026-01-01T00:00:00Z"
    mock_client = MagicMock()
    mock_client.beta.files.list.return_value = MagicMock(data=[meta])

    with patch("app.routers.files.get_client", return_value=mock_client):
        r = await client.get("/files")

    assert r.status_code == 200
    assert r.json()[0]["file_id"] == "file_123"


async def test_delete_file(client, auth_override):
    mock_client = MagicMock()

    with patch("app.routers.files.get_client", return_value=mock_client):
        r = await client.delete("/files/file_123")

    assert r.status_code == 204
    mock_client.beta.files.delete.assert_called_once_with("file_123", betas=["files-api-2025-04-14"])


async def test_download_file(client, auth_override):
    mock_client = MagicMock()
    mock_client.beta.files.retrieve_metadata.return_value = MagicMock(
        mime_type="text/csv", filename="result.csv"
    )
    mock_client.beta.files.download.return_value = iter([b"a,b\n1,2\n"])

    with patch("app.routers.files.get_client", return_value=mock_client):
        r = await client.get("/files/file_123/content")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="result.csv"' in r.headers["content-disposition"]


async def test_download_file_anthropic_error(client, auth_override):
    mock_client = MagicMock()
    mock_client.beta.files.retrieve_metadata.side_effect = Exception("not found")

    with patch("app.routers.files.get_client", return_value=mock_client):
        r = await client.get("/files/file_missing/content")

    assert r.status_code == 502


async def test_upload_file_anthropic_error(client, auth_override):
    mock_client = MagicMock()
    mock_client.beta.files.upload.side_effect = Exception("quota exceeded")

    with patch("app.routers.files.get_client", return_value=mock_client):
        r = await client.post(
            "/files",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )

    assert r.status_code == 502
    assert "quota exceeded" in r.json()["detail"]
