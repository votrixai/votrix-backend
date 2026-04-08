"""Unit tests for opaque storage_path generation.

Covers the public-bucket scheme: ``users/{user_sid}/{agent_sid}{path}_{salt}``
for user files and ``blueprints/{agent_sid}{path}_{salt}`` for blueprint files.

These are pure-function tests with no DB or Supabase Storage dependencies, so
they sidestep the broader integration-test fixture setup.
"""

import re
import string
import uuid

from app.db.queries.blueprint_files import _make_storage_path as bp_make_storage_path
from app.db.queries.user_files import _make_storage_path as uf_make_storage_path
from app.short_id import decode as decode_short_id, encode as encode_short_id


# Base64url alphabet used by ``secrets.token_urlsafe``.
_URLSAFE_CHARS = set(string.ascii_letters + string.digits + "-_")


# ── Blueprint storage paths ──────────────────────────────────────


class TestBlueprintStoragePath:
    def test_starts_with_blueprints_prefix(self):
        agent_id = uuid.uuid4()
        sp = bp_make_storage_path(agent_id, "/logo.png")
        assert sp.startswith("blueprints/")

    def test_contains_short_id_encoded_agent(self):
        agent_id = uuid.uuid4()
        sp = bp_make_storage_path(agent_id, "/logo.png")
        sid = encode_short_id(agent_id)
        assert sp.startswith(f"blueprints/{sid}")
        # The short id must be round-trippable back to the original UUID.
        assert decode_short_id(sid) == agent_id

    def test_does_not_leak_raw_uuid(self):
        """Raw UUID with dashes must not appear in the path — short_id only."""
        agent_id = uuid.uuid4()
        sp = bp_make_storage_path(agent_id, "/logo.png")
        assert str(agent_id) not in sp

    def test_preserves_logical_path(self):
        agent_id = uuid.uuid4()
        sp = bp_make_storage_path(agent_id, "/skills/booking/icon.png")
        assert "/skills/booking/icon.png_" in sp

    def test_salt_separator_present(self):
        agent_id = uuid.uuid4()
        sp = bp_make_storage_path(agent_id, "/logo.png")
        # Salt is appended with `_` after the logical path's filename.
        assert sp.count("_") >= 1
        salt = sp.rsplit("_", 1)[-1]
        assert len(salt) >= 8  # token_urlsafe(8) → ~11 chars

    def test_salt_is_url_safe(self):
        agent_id = uuid.uuid4()
        sp = bp_make_storage_path(agent_id, "/logo.png")
        salt = sp.rsplit("_", 1)[-1]
        assert set(salt) <= _URLSAFE_CHARS

    def test_two_calls_produce_different_salts(self):
        """Salt randomness — two consecutive calls must not collide."""
        agent_id = uuid.uuid4()
        path = "/logo.png"
        results = {bp_make_storage_path(agent_id, path) for _ in range(50)}
        assert len(results) == 50

    def test_different_agents_produce_different_paths(self):
        path = "/logo.png"
        sp1 = bp_make_storage_path(uuid.uuid4(), path)
        sp2 = bp_make_storage_path(uuid.uuid4(), path)
        assert sp1 != sp2

    def test_no_whitespace_in_storage_path(self):
        agent_id = uuid.uuid4()
        sp = bp_make_storage_path(agent_id, "/dir/file.bin")
        assert not re.search(r"\s", sp)


# ── User storage paths ──────────────────────────────────────────


class TestUserStoragePath:
    def test_starts_with_users_prefix(self):
        sp = uf_make_storage_path(uuid.uuid4(), uuid.uuid4(), "/photo.jpg")
        assert sp.startswith("users/")

    def test_contains_both_short_ids(self):
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        sp = uf_make_storage_path(user_id, agent_id, "/photo.jpg")
        user_sid = encode_short_id(user_id)
        agent_sid = encode_short_id(agent_id)
        assert sp.startswith(f"users/{user_sid}/{agent_sid}")

    def test_does_not_leak_raw_uuids(self):
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        sp = uf_make_storage_path(user_id, agent_id, "/photo.jpg")
        assert str(user_id) not in sp
        assert str(agent_id) not in sp

    def test_preserves_logical_path(self):
        sp = uf_make_storage_path(
            uuid.uuid4(), uuid.uuid4(), "/assets/menu/cover.jpg"
        )
        assert "/assets/menu/cover.jpg_" in sp

    def test_salt_separator_present(self):
        sp = uf_make_storage_path(uuid.uuid4(), uuid.uuid4(), "/photo.jpg")
        salt = sp.rsplit("_", 1)[-1]
        assert len(salt) >= 8

    def test_salt_is_url_safe(self):
        sp = uf_make_storage_path(uuid.uuid4(), uuid.uuid4(), "/photo.jpg")
        salt = sp.rsplit("_", 1)[-1]
        assert set(salt) <= _URLSAFE_CHARS

    def test_two_calls_produce_different_salts(self):
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        results = {
            uf_make_storage_path(user_id, agent_id, "/photo.jpg") for _ in range(50)
        }
        assert len(results) == 50

    def test_different_users_produce_different_paths(self):
        agent_id = uuid.uuid4()
        sp1 = uf_make_storage_path(uuid.uuid4(), agent_id, "/photo.jpg")
        sp2 = uf_make_storage_path(uuid.uuid4(), agent_id, "/photo.jpg")
        assert sp1 != sp2

    def test_user_and_blueprint_paths_are_disjoint(self):
        """User storage paths and blueprint storage paths share the same bucket
        but live under disjoint top-level prefixes — guarantees they can never
        collide on a generic filename."""
        agent_id = uuid.uuid4()
        user_id = uuid.uuid4()
        bp_sp = bp_make_storage_path(agent_id, "/logo.png")
        uf_sp = uf_make_storage_path(user_id, agent_id, "/logo.png")
        assert bp_sp.startswith("blueprints/")
        assert uf_sp.startswith("users/")
        assert bp_sp != uf_sp


# ── Cross-cutting unguessability properties ─────────────────────


class TestUnguessability:
    def test_knowing_uuids_and_path_is_not_enough(self):
        """Even with both UUIDs and the logical path, an attacker cannot
        construct the storage path without the salt — that's the whole point
        of going public bucket + salt instead of private + signed URLs."""
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        path = "/avatar.png"

        # An attacker who knows everything except the salt:
        guess = (
            f"users/{encode_short_id(user_id)}/{encode_short_id(agent_id)}{path}"
        )
        actual = uf_make_storage_path(user_id, agent_id, path)

        assert actual.startswith(guess + "_")
        assert actual != guess

    def test_salt_entropy_meets_minimum_bits(self):
        """token_urlsafe(8) → 8 bytes → 64 bits of entropy. The encoded
        string must reflect at least that many bits, i.e. ~11 base64url chars."""
        sp = bp_make_storage_path(uuid.uuid4(), "/x.bin")
        salt = sp.rsplit("_", 1)[-1]
        # 64 bits in base64url ≈ ceil(64/6) = 11 chars
        assert len(salt) >= 11
