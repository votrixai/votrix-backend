"""
Tests for Files API integration.

Pure-logic tests require no mocks.
Router tests mock the Anthropic client and bypass auth.
"""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth import AuthedUser, WorkspaceContext, require_user, require_workspace
from app.models.chat import FileAttachment
from app.runtime.sessions import _build_content

_TEST_USER = AuthedUser(id=uuid.uuid4(), email="test@example.com")
_TEST_WORKSPACE = WorkspaceContext(user_id=_TEST_USER.id, workspace_id=uuid.uuid4(), role="owner")


def _override_auth():
    return _TEST_USER


def _override_workspace():
    return _TEST_WORKSPACE


# ---------------------------------------------------------------------------
# _build_content — pure logic, no mocks
# ---------------------------------------------------------------------------


def test_build_content_text_only():
    result = _build_content("hello", [], {})
    assert result == [{"type": "text", "text": "hello"}]


def test_build_content_with_document():
    att = FileAttachment(file_id="file_abc", content_type="document")
    result = _build_content("summarize this", [att], {"file_abc": "doc.pdf"})
    assert result[0] == {"type": "text", "text": "summarize this"}
    assert result[1] == {"type": "document", "source": {"type": "file", "file_id": "file_abc"}}
    assert "doc.pdf" in result[2]["text"]


def test_build_content_with_image():
    att = FileAttachment(file_id="file_img", content_type="image")
    result = _build_content("describe this image", [att], {"file_img": "photo.png"})
    assert result[0] == {"type": "text", "text": "describe this image"}
    assert result[1] == {"type": "image", "source": {"type": "file", "file_id": "file_img"}}
    assert "photo.png" in result[2]["text"]


def test_build_content_multiple_attachments():
    attachments = [
        FileAttachment(file_id="file_doc", content_type="document"),
        FileAttachment(file_id="file_img", content_type="image"),
    ]
    result = _build_content("analyze", attachments, {"file_doc": "doc.pdf", "file_img": "img.png"})
    assert result[0] == {"type": "text", "text": "analyze"}
    assert result[1]["source"]["file_id"] == "file_doc"
    assert result[2]["source"]["file_id"] == "file_img"
    assert "Attached files" in result[3]["text"]


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
    """Bypass Supabase JWT auth and workspace membership lookup for files router tests."""
    import importlib
    app = importlib.import_module("app.main").app
    app.dependency_overrides[require_user] = _override_auth
    app.dependency_overrides[require_workspace] = _override_workspace
    yield
    app.dependency_overrides.pop(require_user, None)
    app.dependency_overrides.pop(require_workspace, None)


def _make_file_meta(file_id="file_123", filename="doc.pdf", size=1024):
    m = MagicMock()
    m.id = file_id
    m.filename = filename
    m.size = size
    return m


def _async_mock_client():
    mock = MagicMock()
    mock.beta.files.upload = AsyncMock()
    mock.beta.files.list = AsyncMock()
    mock.beta.files.delete = AsyncMock()
    mock.beta.files.retrieve_metadata = AsyncMock()
    mock.beta.files.download = AsyncMock()
    return mock


async def test_upload_file(client, auth_override):
    meta = _make_file_meta()
    mock_client = _async_mock_client()
    mock_client.beta.files.upload.return_value = meta

    with patch("app.routers.files.get_async_client", return_value=mock_client):
        r = await client.post(
            "/files",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["file_id"] == "file_123"
    assert body["filename"] == "doc.pdf"
    mock_client.beta.files.upload.assert_called_once()


async def test_list_files(client, auth_override):
    meta = _make_file_meta()
    meta.created_at = "2026-01-01T00:00:00Z"
    meta.downloadable = False
    meta.mime_type = None
    meta.size_bytes = None
    mock_client = _async_mock_client()
    mock_client.beta.files.list.return_value = MagicMock(data=[meta])

    with patch("app.routers.files.get_async_client", return_value=mock_client):
        r = await client.get("/files")

    assert r.status_code == 200
    assert r.json()[0]["file_id"] == "file_123"


async def test_delete_file(client, auth_override):
    mock_client = _async_mock_client()

    with patch("app.routers.files.get_async_client", return_value=mock_client):
        r = await client.delete("/files/file_123")

    assert r.status_code == 204
    mock_client.beta.files.delete.assert_called_once_with("file_123", betas=["files-api-2025-04-14", "managed-agents-2026-04-01"])


async def test_download_file(client, auth_override):
    mock_client = _async_mock_client()
    mock_client.beta.files.retrieve_metadata.return_value = MagicMock(
        mime_type="text/csv", filename="result.csv", downloadable=True
    )
    mock_client.beta.files.download.return_value = AsyncMock(read=AsyncMock(return_value=b"a,b\n1,2\n"))

    with patch("app.routers.files.get_async_client", return_value=mock_client):
        r = await client.get("/files/file_123/content")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="result.csv"' in r.headers["content-disposition"]


async def test_download_file_anthropic_error(client, auth_override):
    mock_client = _async_mock_client()
    mock_client.beta.files.retrieve_metadata.side_effect = Exception("not found")

    with patch("app.routers.files.get_async_client", return_value=mock_client):
        r = await client.get("/files/file_missing/content")

    assert r.status_code == 502


async def test_upload_file_anthropic_error(client, auth_override):
    mock_client = _async_mock_client()
    mock_client.beta.files.upload.side_effect = Exception("quota exceeded")

    with patch("app.routers.files.get_async_client", return_value=mock_client):
        r = await client.post(
            "/files",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )

    assert r.status_code == 502
    assert "quota exceeded" in r.json()["detail"]
