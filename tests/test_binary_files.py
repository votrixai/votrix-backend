"""Tests for hybrid file storage — text in Postgres, binary in Supabase Storage.

All Supabase Storage calls are mocked. DB operations run against real SQLite.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.db.queries.orgs import create_org, delete_org
from app.db.queries.agents import create_agent, delete_agent
from app.db.queries.end_user_accounts import create_end_user_account, delete_end_user_account
from app.db.queries import blueprint_files as bf
from app.db.queries import user_files as uf
from app.db.queries.end_user_agent_links import replicate_blueprint_to_user, link_agent


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
async def agent_id(session):
    org = await create_org(session, display_name="O")
    await session.commit()
    row = await create_agent(session, org.id, name="A")
    return row["id"]


@pytest.fixture
async def user_ids(session):
    """Return (agent_id, user_id)."""
    org = await create_org(session, display_name="O")
    await session.commit()
    agent = await create_agent(session, org.id, name="A")
    user = await create_end_user_account(session, org.id, display_name="U")
    await session.commit()
    return agent["id"], user.id


@pytest.fixture
async def full_ids(session):
    """Return (org_id, agent_id, user_id) for cascade delete tests."""
    org = await create_org(session, display_name="O")
    await session.commit()
    agent = await create_agent(session, org.id, name="A")
    user = await create_end_user_account(session, org.id, display_name="U")
    await session.commit()
    return org.id, agent["id"], user.id


@pytest.fixture
def mock_storage():
    """Mock all Supabase Storage calls. Tracks uploaded/deleted paths."""
    store = {}

    async def _upload(bucket, path, data, mime_type):
        store[path] = {"data": data, "mime_type": mime_type}
        return path

    async def _download(bucket, path):
        if path not in store:
            raise FileNotFoundError(f"Not in mock storage: {path}")
        return store[path]["data"]

    async def _delete(bucket, path):
        store.pop(path, None)

    async def _copy(bucket, src, dst, mime_type="application/octet-stream"):
        if src in store:
            store[dst] = {"data": store[src]["data"], "mime_type": mime_type}
        return dst

    with (
        patch("app.db.queries.blueprint_files.storage_upload", side_effect=_upload),
        patch("app.db.queries.blueprint_files.storage_delete", side_effect=_delete),
        patch("app.db.queries.user_files.storage_upload", side_effect=_upload),
        patch("app.db.queries.user_files.storage_delete", side_effect=_delete),
        patch("app.db.queries.agents.storage_delete", side_effect=_delete),
        patch("app.db.queries.orgs.storage_delete", side_effect=_delete),
        patch("app.db.queries.end_user_accounts.storage_delete", side_effect=_delete),
        patch("app.storage.upload_file", side_effect=_upload),
        patch("app.storage.download_file", side_effect=_download),
        patch("app.storage.delete_file", side_effect=_delete),
        patch("app.storage.copy_file", side_effect=_copy),
        patch("app.db.queries.end_user_agent_links.download_file", side_effect=_download),
        patch("app.routers.agents.download_file", side_effect=_download),
    ):
        yield store


# ══════════════════════════════════════════════════════════════
# Blueprint file tests — binary
# ══════════════════════════════════════════════════════════════


class TestBlueprintBinaryWrite:
    async def test_write_binary_sets_storage_path(self, session, agent_id, mock_storage):
        row = await bf.write_file(
            session, agent_id, "/logo.png",
            mime_type="image/png",
            binary_data=b"\x89PNG\r\n\x1a\n",
        )
        assert row["storage_path"] is not None
        assert row["content"] is None
        assert row["size_bytes"] == 8
        assert row["mime_type"] == "image/png"

    async def test_write_binary_uploads_to_storage(self, session, agent_id, mock_storage):
        data = b"\x89PNG fake image"
        await bf.write_file(
            session, agent_id, "/img.png",
            mime_type="image/png",
            binary_data=data,
        )
        # Verify it's in mock storage
        expected_key = f"blueprints/{agent_id}/img.png"
        assert expected_key in mock_storage
        assert mock_storage[expected_key]["data"] == data

    async def test_write_text_no_storage_path(self, session, agent_id, mock_storage):
        row = await bf.write_file(session, agent_id, "/readme.md", "# Hello")
        assert row["storage_path"] is None
        assert row["content"] == "# Hello"
        assert len(mock_storage) == 0

    async def test_text_mime_via_upload_decoded(self, session, agent_id, mock_storage):
        """Uploading binary_data with text MIME → decoded to string in Postgres."""
        row = await bf.write_file(
            session, agent_id, "/data.json",
            mime_type="application/json",
            binary_data=b'{"key": "value"}',
        )
        assert row["storage_path"] is None
        assert row["content"] == '{"key": "value"}'
        assert len(mock_storage) == 0


class TestBlueprintBinaryRead:
    async def test_read_binary_returns_storage_path(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/doc.pdf",
            mime_type="application/pdf",
            binary_data=b"%PDF-1.4 fake",
        )
        f = await bf.read_file(session, agent_id, "/doc.pdf")
        assert f is not None
        assert f["content"] is None
        assert f["storage_path"] is not None
        assert "doc.pdf" in f["storage_path"]

    async def test_read_text_no_storage_path(self, session, agent_id, mock_storage):
        await bf.write_file(session, agent_id, "/note.md", "hello")
        f = await bf.read_file(session, agent_id, "/note.md")
        assert f["content"] == "hello"
        assert f["storage_path"] is None


class TestBlueprintBinaryOverwrite:
    async def test_overwrite_binary_with_text_cleans_storage(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/file.dat",
            mime_type="application/octet-stream",
            binary_data=b"binary data",
        )
        assert len(mock_storage) == 1

        # Overwrite with text
        await bf.write_file(session, agent_id, "/file.dat", "now text", mime_type="text/plain")
        f = await bf.read_file(session, agent_id, "/file.dat")
        assert f["content"] == "now text"
        assert f["storage_path"] is None
        assert len(mock_storage) == 0  # old storage cleaned up

    async def test_overwrite_binary_with_new_binary(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/img.png",
            mime_type="image/png",
            binary_data=b"v1",
        )
        await bf.write_file(
            session, agent_id, "/img.png",
            mime_type="image/png",
            binary_data=b"v2",
        )
        f = await bf.read_file(session, agent_id, "/img.png")
        assert f["content"] is None
        assert f["storage_path"] is not None
        # Old storage cleaned, new one present
        key = f"blueprints/{agent_id}/img.png"
        assert mock_storage[key]["data"] == b"v2"

    async def test_overwrite_text_with_binary(self, session, agent_id, mock_storage):
        await bf.write_file(session, agent_id, "/f.txt", "text content")
        await bf.write_file(
            session, agent_id, "/f.txt",
            mime_type="image/jpeg",
            binary_data=b"\xff\xd8\xff",
        )
        f = await bf.read_file(session, agent_id, "/f.txt")
        assert f["content"] is None
        assert f["storage_path"] is not None


class TestBlueprintBinaryEdit:
    async def test_edit_binary_returns_none(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/data.db",
            mime_type="application/x-sqlite3",
            binary_data=b"SQLite format 3",
        )
        result = await bf.edit_file(session, agent_id, "/data.db", "old", "new")
        assert result is None


class TestBlueprintBinaryGrep:
    async def test_grep_matches_binary_by_name(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/assets/logo.png",
            mime_type="image/png",
            binary_data=b"PNG",
        )
        await bf.write_file(session, agent_id, "/readme.md", "hello world")
        results = await bf.grep(session, agent_id, "logo")
        assert len(results) == 1
        assert results[0]["path"] == "/assets/logo.png"
        assert results[0]["matches"] == ["[binary file]"]

    async def test_grep_matches_text_content_not_binary(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/data.bin",
            mime_type="application/octet-stream",
            binary_data=b"hello",
        )
        await bf.write_file(session, agent_id, "/doc.md", "hello world")
        results = await bf.grep(session, agent_id, "hello")
        # Only the text file matches on content
        text_matches = [r for r in results if r["matches"] != ["[binary file]"]]
        assert len(text_matches) == 1
        assert text_matches[0]["path"] == "/doc.md"

    async def test_grep_no_match_binary_content(self, session, agent_id, mock_storage):
        """Binary file content is NOT searched, only name/path."""
        await bf.write_file(
            session, agent_id, "/secret.bin",
            mime_type="application/octet-stream",
            binary_data=b"supersecret",
        )
        results = await bf.grep(session, agent_id, "supersecret")
        assert len(results) == 0


class TestBlueprintBinaryDelete:
    async def test_rm_cleans_storage(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/del.bin",
            mime_type="application/octet-stream",
            binary_data=b"data",
        )
        assert len(mock_storage) == 1
        await bf.rm(session, agent_id, "/del.bin")
        assert len(mock_storage) == 0
        assert not await bf.exists(session, agent_id, "/del.bin")

    async def test_rm_rf_cleans_storage(self, session, agent_id, mock_storage):
        await bf.mkdir(session, agent_id, "/assets")
        await bf.write_file(
            session, agent_id, "/assets/a.png",
            mime_type="image/png", binary_data=b"a",
        )
        await bf.write_file(
            session, agent_id, "/assets/b.jpg",
            mime_type="image/jpeg", binary_data=b"b",
        )
        await bf.write_file(session, agent_id, "/assets/c.md", "text")
        assert len(mock_storage) == 2  # only binary files

        count = await bf.rm_rf(session, agent_id, "/assets")
        assert count == 4  # dir + 3 files
        assert len(mock_storage) == 0


class TestBlueprintBinaryMv:
    async def test_mv_binary_updates_storage(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/old.png",
            mime_type="image/png", binary_data=b"img",
        )
        old_key = f"blueprints/{agent_id}/old.png"
        assert old_key in mock_storage

        await bf.mv(session, agent_id, "/old.png", "/new.png")
        new_key = f"blueprints/{agent_id}/new.png"
        assert old_key not in mock_storage
        assert new_key in mock_storage

        f = await bf.read_file(session, agent_id, "/new.png")
        assert f["storage_path"] == new_key

    async def test_mv_text_no_storage_op(self, session, agent_id, mock_storage):
        await bf.write_file(session, agent_id, "/old.md", "content")
        await bf.mv(session, agent_id, "/old.md", "/new.md")
        assert len(mock_storage) == 0
        f = await bf.read_file(session, agent_id, "/new.md")
        assert f["content"] == "content"


class TestBlueprintMkdirOverwrite:
    async def test_mkdir_over_binary_cleans_storage(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/dir",
            mime_type="application/octet-stream",
            binary_data=b"was a file",
        )
        assert len(mock_storage) == 1
        await bf.mkdir(session, agent_id, "/dir")
        assert len(mock_storage) == 0
        f = await bf.read_file(session, agent_id, "/dir")
        assert f["type"] == "directory"


# ══════════════════════════════════════════════════════════════
# User file tests — binary
# ══════════════════════════════════════════════════════════════


class TestUserBinaryWrite:
    async def test_write_binary(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        row = await uf.write_file(
            session, aid, uid, "/photo.jpg",
            mime_type="image/jpeg",
            binary_data=b"\xff\xd8\xff",
        )
        assert row["storage_path"] is not None
        assert row["content"] is None

    async def test_write_text(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        row = await uf.write_file(session, aid, uid, "/note.md", "hello")
        assert row["storage_path"] is None
        assert row["content"] == "hello"

    async def test_text_mime_binary_data_decoded(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        row = await uf.write_file(
            session, aid, uid, "/script.sh",
            mime_type="application/x-sh",
            binary_data=b"#!/bin/bash\necho hi",
        )
        assert row["content"] == "#!/bin/bash\necho hi"
        assert row["storage_path"] is None


class TestUserBinaryDelete:
    async def test_rm_cleans_storage(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        await uf.write_file(
            session, aid, uid, "/rm.bin",
            mime_type="application/octet-stream", binary_data=b"x",
        )
        assert len(mock_storage) == 1
        await uf.rm(session, aid, uid, "/rm.bin")
        assert len(mock_storage) == 0

    async def test_rm_rf_cleans_storage(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        await uf.mkdir(session, aid, uid, "/assets")
        await uf.write_file(
            session, aid, uid, "/assets/img.png",
            mime_type="image/png", binary_data=b"img",
        )
        assert len(mock_storage) == 1
        count = await uf.rm_rf(session, aid, uid, "/assets")
        assert count == 2
        assert len(mock_storage) == 0

    async def test_delete_files_cleans_storage(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        await uf.write_file(
            session, aid, uid, "/a.bin",
            mime_type="application/octet-stream", binary_data=b"a",
        )
        await uf.write_file(session, aid, uid, "/b.md", "text")
        assert len(mock_storage) == 1
        count = await uf.delete_files(session, aid, uid, ["/a.bin", "/b.md"])
        assert count == 2
        assert len(mock_storage) == 0


class TestUserBinaryMv:
    async def test_mv_binary(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        await uf.write_file(
            session, aid, uid, "/old.bin",
            mime_type="application/octet-stream", binary_data=b"data",
        )
        old_key = f"users/{uid}/{aid}/old.bin"
        assert old_key in mock_storage

        await uf.mv(session, aid, uid, "/old.bin", "/new.bin")
        new_key = f"users/{uid}/{aid}/new.bin"
        assert old_key not in mock_storage
        assert new_key in mock_storage


# ══════════════════════════════════════════════════════════════
# Replication tests — binary
# ══════════════════════════════════════════════════════════════


class TestReplicationBinary:
    async def test_replicate_text_files(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        await bf.write_file(session, aid, "/doc.md", "hello")
        await link_agent(session, uid, aid)
        count = await replicate_blueprint_to_user(session, aid, uid)
        assert count == 1
        f = await uf.read_file(session, aid, uid, "/doc.md")
        assert f["content"] == "hello"
        assert f["storage_path"] is None

    async def test_replicate_binary_files(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        await bf.write_file(
            session, aid, "/logo.png",
            mime_type="image/png", binary_data=b"PNG data",
        )
        await link_agent(session, uid, aid)
        count = await replicate_blueprint_to_user(session, aid, uid)
        assert count == 1

        f = await uf.read_file(session, aid, uid, "/logo.png")
        assert f["content"] is None
        assert f["storage_path"] is not None
        # User storage path is different from blueprint storage path
        assert f["storage_path"].startswith(f"users/{uid}/")

    async def test_replicate_mixed(self, session, user_ids, mock_storage):
        aid, uid = user_ids
        await bf.mkdir(session, aid, "/assets")
        await bf.write_file(session, aid, "/readme.md", "text")
        await bf.write_file(
            session, aid, "/assets/img.png",
            mime_type="image/png", binary_data=b"img",
        )
        await link_agent(session, uid, aid)
        count = await replicate_blueprint_to_user(session, aid, uid)
        assert count == 3  # dir + text + binary

        text = await uf.read_file(session, aid, uid, "/readme.md")
        assert text["content"] == "text"
        assert text["storage_path"] is None

        img = await uf.read_file(session, aid, uid, "/assets/img.png")
        assert img["content"] is None
        assert img["storage_path"] is not None


# ══════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    async def test_empty_binary_file(self, session, agent_id, mock_storage):
        row = await bf.write_file(
            session, agent_id, "/empty.bin",
            mime_type="application/octet-stream",
            binary_data=b"",
        )
        assert row["storage_path"] is not None
        assert row["content"] is None
        assert row["size_bytes"] == 0

    async def test_write_no_content_no_binary(self, session, agent_id, mock_storage):
        """JSON endpoint with content=None, no binary_data → empty text file."""
        row = await bf.write_file(session, agent_id, "/empty.md")
        assert row["content"] == ""
        assert row["storage_path"] is None
        assert row["size_bytes"] == 0

    async def test_binary_file_in_glob(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/assets/logo.png",
            mime_type="image/png", binary_data=b"PNG",
        )
        await bf.write_file(session, agent_id, "/assets/style.css", "body {}")
        results = await bf.glob(session, agent_id, "/assets/*")
        paths = [r["path"] for r in results]
        assert "/assets/logo.png" in paths
        assert "/assets/style.css" in paths

    async def test_binary_file_in_tree(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/data.db",
            mime_type="application/x-sqlite3", binary_data=b"SQLite",
        )
        entries = await bf.tree(session, agent_id)
        assert any(e["path"] == "/data.db" for e in entries)

    async def test_binary_file_in_ls(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/video.mp4",
            mime_type="video/mp4", binary_data=b"moov",
        )
        entries = await bf.ls(session, agent_id, "/")
        assert len(entries) == 1
        assert entries[0]["mime_type"] == "video/mp4"

    async def test_stat_binary_file(self, session, agent_id, mock_storage):
        await bf.write_file(
            session, agent_id, "/doc.pdf",
            mime_type="application/pdf", binary_data=b"%PDF",
        )
        s = await bf.stat(session, agent_id, "/doc.pdf")
        assert s is not None
        assert s["mime_type"] == "application/pdf"
        assert s["size_bytes"] == 4

    async def test_get_all_files_includes_binary(self, session, agent_id, mock_storage):
        await bf.write_file(session, agent_id, "/a.md", "text")
        await bf.write_file(
            session, agent_id, "/b.bin",
            mime_type="application/octet-stream", binary_data=b"bin",
        )
        all_files = await bf.get_all_files(session, agent_id)
        assert len(all_files) == 2
        text_f = next(f for f in all_files if f["path"] == "/a.md")
        bin_f = next(f for f in all_files if f["path"] == "/b.bin")
        assert text_f["content"] == "text"
        assert text_f["storage_path"] is None
        assert bin_f["content"] is None
        assert bin_f["storage_path"] is not None

    async def test_utf8_decode_error_replaced(self, session, agent_id, mock_storage):
        """Binary data with text MIME that isn't valid UTF-8 → replacement chars."""
        row = await bf.write_file(
            session, agent_id, "/bad.txt",
            mime_type="text/plain",
            binary_data=b"hello \xff\xfe world",
        )
        assert row["storage_path"] is None
        assert "\ufffd" in row["content"]  # replacement character
        assert "hello" in row["content"]


# ══════════════════════════════════════════════════════════════
# Cascade delete tests — storage cleanup
# ══════════════════════════════════════════════════════════════


class TestDeleteAgentCascade:
    async def test_delete_agent_cleans_blueprint_storage(self, session, full_ids, mock_storage):
        _, aid, _ = full_ids
        await bf.write_file(
            session, aid, "/logo.png",
            mime_type="image/png", binary_data=b"PNG",
        )
        await bf.write_file(session, aid, "/readme.md", "text")
        assert len(mock_storage) == 1

        await delete_agent(session, aid)
        assert len(mock_storage) == 0

    async def test_delete_agent_cleans_user_file_storage(self, session, full_ids, mock_storage):
        _, aid, uid = full_ids
        await link_agent(session, uid, aid)
        await replicate_blueprint_to_user(session, aid, uid)

        # Write a binary user file
        await uf.write_file(
            session, aid, uid, "/user.bin",
            mime_type="application/octet-stream", binary_data=b"user data",
        )
        assert len(mock_storage) == 1

        await delete_agent(session, aid)
        assert len(mock_storage) == 0


class TestDeleteUserAccountCascade:
    async def test_delete_user_cleans_storage(self, session, full_ids, mock_storage):
        _, aid, uid = full_ids
        await uf.write_file(
            session, aid, uid, "/photo.jpg",
            mime_type="image/jpeg", binary_data=b"\xff\xd8\xff",
        )
        await uf.write_file(
            session, aid, uid, "/doc.pdf",
            mime_type="application/pdf", binary_data=b"%PDF",
        )
        assert len(mock_storage) == 2

        await delete_end_user_account(session, uid)
        assert len(mock_storage) == 0

    async def test_delete_user_ignores_text_files(self, session, full_ids, mock_storage):
        _, aid, uid = full_ids
        await uf.write_file(session, aid, uid, "/note.md", "text")
        assert len(mock_storage) == 0

        await delete_end_user_account(session, uid)
        assert len(mock_storage) == 0  # nothing to clean


class TestDeleteOrgCascade:
    async def test_delete_org_cleans_all_storage(self, session, full_ids, mock_storage):
        org_id, aid, uid = full_ids
        # Blueprint binary
        await bf.write_file(
            session, aid, "/bp.png",
            mime_type="image/png", binary_data=b"bp",
        )
        # User binary
        await uf.write_file(
            session, aid, uid, "/uf.bin",
            mime_type="application/octet-stream", binary_data=b"uf",
        )
        assert len(mock_storage) == 2

        await delete_org(session, org_id)
        assert len(mock_storage) == 0


# ══════════════════════════════════════════════════════════════
# Seed-from (agent cloning) tests — binary
# ══════════════════════════════════════════════════════════════


class TestSeedFromBinary:
    async def test_seed_clones_text_files(self, session, full_ids, mock_storage):
        org_id, src_aid, _ = full_ids
        await bf.write_file(session, src_aid, "/doc.md", "hello")

        new_agent = await create_agent(session, org_id, name="Clone")
        new_id = new_agent["id"]

        # Manually replicate seed_from logic
        source_files = await bf.tree(session, src_aid)
        for f in source_files:
            if f["type"] == "directory":
                await bf.mkdir(session, new_id, f["path"])
            else:
                content_row = await bf.read_file(session, src_aid, f["path"])
                if content_row:
                    if content_row.get("storage_path"):
                        from app.storage import download_file
                        data = await download_file("files", content_row["storage_path"])
                        await bf.write_file(
                            session, new_id, f["path"],
                            mime_type=content_row.get("mime_type", "application/octet-stream"),
                            binary_data=data,
                        )
                    else:
                        await bf.write_file(
                            session, new_id, f["path"],
                            content_row.get("content") or "",
                            mime_type=content_row.get("mime_type", "text/markdown"),
                        )

        cloned = await bf.read_file(session, new_id, "/doc.md")
        assert cloned is not None
        assert cloned["content"] == "hello"
        assert cloned["storage_path"] is None

    async def test_seed_clones_binary_files(self, session, full_ids, mock_storage):
        org_id, src_aid, _ = full_ids
        await bf.write_file(
            session, src_aid, "/logo.png",
            mime_type="image/png", binary_data=b"PNG data",
        )

        new_agent = await create_agent(session, org_id, name="Clone")
        new_id = new_agent["id"]

        source_files = await bf.tree(session, src_aid)
        for f in source_files:
            if f["type"] != "directory":
                content_row = await bf.read_file(session, src_aid, f["path"])
                if content_row and content_row.get("storage_path"):
                    from app.storage import download_file
                    data = await download_file("files", content_row["storage_path"])
                    await bf.write_file(
                        session, new_id, f["path"],
                        mime_type=content_row.get("mime_type", "application/octet-stream"),
                        binary_data=data,
                    )

        cloned = await bf.read_file(session, new_id, "/logo.png")
        assert cloned is not None
        assert cloned["content"] is None
        assert cloned["storage_path"] is not None
        # Cloned storage path should be different from source
        src = await bf.read_file(session, src_aid, "/logo.png")
        assert cloned["storage_path"] != src["storage_path"]
