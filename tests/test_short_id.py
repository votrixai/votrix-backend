"""Tests for prefixed short ID encoding/decoding and middleware."""

import uuid

import pytest

from app.short_id import (
    decode,
    decode_prefixed,
    encode,
    encode_prefixed,
    _encode_response,
    _decode_request_body,
    _is_uuid_str,
    _id_prefix_from_path,
)


# ── encode / decode roundtrip ─────────────────────────────────


class TestEncodeDecode:
    def test_roundtrip_random(self):
        for _ in range(100):
            u = uuid.uuid4()
            assert decode(encode(u)) == u

    def test_roundtrip_nil(self):
        u = uuid.UUID(int=0)
        assert decode(encode(u)) == u

    def test_roundtrip_max(self):
        u = uuid.UUID(int=(2**128) - 1)
        assert decode(encode(u)) == u

    def test_encode_produces_no_hyphens(self):
        assert "-" not in encode(uuid.uuid4())

    def test_short_id_length(self):
        assert 1 <= len(encode(uuid.uuid4())) <= 22

    def test_decode_invalid_char(self):
        with pytest.raises(ValueError):
            decode("abc-def")

    def test_decode_overflow(self):
        with pytest.raises((ValueError, OverflowError)):
            decode("A" * 50)


# ── prefixed encode / decode ──────────────────────────────────


class TestPrefixed:
    def test_encode_prefixed(self):
        u = uuid.uuid4()
        result = encode_prefixed(u, "org")
        assert result.startswith("org_")
        assert decode_prefixed(result) == u

    def test_encode_no_prefix(self):
        u = uuid.uuid4()
        result = encode_prefixed(u, "")
        assert "_" not in result
        assert decode(result) == u

    def test_decode_prefixed_strips_prefix(self):
        u = uuid.uuid4()
        short = f"agent_{encode(u)}"
        assert decode_prefixed(short) == u

    def test_decode_prefixed_raw_uuid(self):
        u = uuid.uuid4()
        assert decode_prefixed(str(u)) == u

    def test_all_prefixes(self):
        u = uuid.uuid4()
        for prefix in ("org", "agent", "user", "link", "integ", "tool", "bai", "bat", "file"):
            encoded = encode_prefixed(u, prefix)
            assert encoded.startswith(f"{prefix}_")
            assert decode_prefixed(encoded) == u


# ── path prefix inference ─────────────────────────────────────


class TestIdPrefixFromPath:
    def test_orgs(self):
        assert _id_prefix_from_path("/orgs") == "org"
        assert _id_prefix_from_path("/orgs/some-id") == "org"

    def test_agents(self):
        assert _id_prefix_from_path("/orgs/x/agents") == "agent"
        assert _id_prefix_from_path("/agents/x") == "agent"

    def test_users(self):
        assert _id_prefix_from_path("/orgs/x/users") == "user"
        assert _id_prefix_from_path("/users/x") == "user"

    def test_user_agents_are_links(self):
        assert _id_prefix_from_path("/users/x/agents") == "link"

    def test_integrations(self):
        assert _id_prefix_from_path("/agents/x/integrations") == "bai"

    def test_tools(self):
        assert _id_prefix_from_path("/agents/x/integrations/y/tools") == "bat"

    def test_files(self):
        assert _id_prefix_from_path("/agents/x/files") == "file"
        assert _id_prefix_from_path("/users/x/agents/y/files") == "file"
        assert _id_prefix_from_path("/agents/x/files/read") == "file"


# ── JSON response encoder ────────────────────────────────────


class TestEncodeResponse:
    def test_encodes_id_with_prefix(self):
        u = uuid.uuid4()
        result = _encode_response({"id": str(u), "name": "test"}, "org")
        assert result["id"].startswith("org_")
        assert result["name"] == "test"

    def test_encodes_fk_fields(self):
        org = uuid.uuid4()
        agent = uuid.uuid4()
        result = _encode_response(
            {"id": str(agent), "org_id": str(org)}, "agent",
        )
        assert result["id"].startswith("agent_")
        assert result["org_id"].startswith("org_")

    def test_encodes_list(self):
        u = uuid.uuid4()
        result = _encode_response([{"id": str(u)}], "org")
        assert result[0]["id"].startswith("org_")

    def test_non_uuid_strings_unchanged(self):
        result = _encode_response({"name": "hello", "path": "/foo"}, "org")
        assert result == {"name": "hello", "path": "/foo"}

    def test_non_string_values_unchanged(self):
        result = _encode_response({"count": 42, "active": True}, "org")
        assert result == {"count": 42, "active": True}


# ── JSON request body decoder ────────────────────────────────


class TestDecodeRequestBody:
    def test_decodes_prefixed_id(self):
        u = uuid.uuid4()
        short = encode_prefixed(u, "agent")
        result = _decode_request_body({"blueprint_agent_id": short})
        assert result["blueprint_agent_id"] == str(u)

    def test_leaves_non_prefixed(self):
        result = _decode_request_body({"name": "hello"})
        assert result == {"name": "hello"}

    def test_leaves_uuid_string(self):
        u = str(uuid.uuid4())
        # UUID strings contain hyphens, not a prefixed ID
        result = _decode_request_body({"id": u})
        assert result["id"] == u


# ── Middleware integration tests ──────────────────────────────


class TestMiddlewareIntegration:
    async def test_org_ids_prefixed(self, client):
        r = await client.post("/orgs", json={"display_name": "TestOrg"})
        assert r.status_code == 201
        org = r.json()
        assert org["id"].startswith("org_")

    async def test_short_id_in_path_resolves(self, client):
        r = await client.post("/orgs", json={"display_name": "PathTest"})
        org_id = r.json()["id"]
        assert org_id.startswith("org_")

        r = await client.get(f"/orgs/{org_id}")
        assert r.status_code == 200
        assert r.json()["display_name"] == "PathTest"

    async def test_agent_crud_with_prefixed_ids(self, client):
        org = (await client.post("/orgs", json={"display_name": "O"})).json()
        org_id = org["id"]

        r = await client.post(f"/orgs/{org_id}/agents", json={"display_name": "Bot"})
        assert r.status_code == 201
        agent = r.json()
        assert agent["id"].startswith("agent_")
        assert agent["org_id"].startswith("org_")
        assert agent["org_id"] == org_id

        agent_id = agent["id"]
        r = await client.get(f"/agents/{agent_id}")
        assert r.status_code == 200
        assert r.json()["display_name"] == "Bot"

    async def test_user_crud_with_prefixed_ids(self, client):
        org = (await client.post("/orgs", json={"display_name": "O"})).json()

        r = await client.post(f"/orgs/{org['id']}/users", json={"display_name": "U"})
        assert r.status_code == 201
        user = r.json()
        assert user["id"].startswith("user_")
        assert user["org_id"].startswith("org_")

    async def test_file_ops_with_prefixed_ids(self, client):
        org = (await client.post("/orgs", json={"display_name": "O"})).json()
        agent = (await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "A"})).json()
        aid = agent["id"]

        r = await client.post(f"/agents/{aid}/files", json={"path": "/test.md", "content": "hi"})
        assert r.status_code == 201

        r = await client.get(f"/agents/{aid}/files/read", params={"path": "/test.md"})
        assert r.status_code == 200
        assert r.json()["content"] == "hi"

    async def test_user_agent_instantiation(self, client):
        org = (await client.post("/orgs", json={"display_name": "O"})).json()
        agent = (await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "A"})).json()
        aid = agent["id"]

        await client.post(f"/agents/{aid}/files", json={"path": "/doc.md", "content": "hello"})

        user = (await client.post(f"/orgs/{org['id']}/users", json={"display_name": "U"})).json()
        uid = user["id"]

        # body contains prefixed short ID
        r = await client.post(f"/users/{uid}/agents", json={"blueprint_agent_id": aid})
        assert r.status_code == 201
        link = r.json()
        assert link["id"].startswith("link_")
        assert link["blueprint_agent_id"] == aid
        assert link["end_user_account_id"] == uid

        # file access via prefixed IDs
        r = await client.get(f"/users/{uid}/agents/{aid}/files/read", params={"path": "/doc.md"})
        assert r.status_code == 200
        assert r.json()["content"] == "hello"

    async def test_raw_uuid_still_works(self, client):
        """Backwards compat — raw UUID in path still resolves."""
        r = await client.post("/orgs", json={"display_name": "RawUUID"})
        short_id = r.json()["id"]
        raw_uuid = str(decode_prefixed(short_id))

        r = await client.get(f"/orgs/{raw_uuid}")
        assert r.status_code == 200
        assert r.json()["display_name"] == "RawUUID"

    async def test_404_with_prefixed_id(self, client):
        fake = encode_prefixed(uuid.uuid4(), "org")
        r = await client.get(f"/orgs/{fake}")
        assert r.status_code == 404

    async def test_list_endpoints_use_prefixes(self, client):
        org = (await client.post("/orgs", json={"display_name": "ListTest"})).json()
        await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "A1"})
        await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "A2"})

        r = await client.get(f"/orgs/{org['id']}/agents")
        assert r.status_code == 200
        agents = r.json()
        assert len(agents) == 2
        for a in agents:
            assert a["id"].startswith("agent_")
