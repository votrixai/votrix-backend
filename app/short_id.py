"""Prefixed short IDs — Clerk/Stripe-style at the API boundary.

Encodes UUIDs as ``org_5EfYQqOSKIci0am84NcpwW``, ``agent_7xBm3nQp...``, etc.
DB stays UUID internally. A single middleware handles both directions:

  Request  →  ``org_5EfYQ...`` in path / body  →  UUID string for routers
  Response →  UUID string from DB              →  ``org_5EfYQ...`` for client

No changes needed in routers, models, or query helpers.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any
from urllib.parse import parse_qsl, urlencode

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ── Base62 codec ──────────────────────────────────────────────

_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE = len(_ALPHABET)  # 62
_REVERSE = {c: i for i, c in enumerate(_ALPHABET)}


def encode(u: uuid.UUID) -> str:
    """Encode a UUID to a base62 string (no prefix)."""
    n = u.int
    if n == 0:
        return _ALPHABET[0]
    chars = []
    while n:
        n, rem = divmod(n, _BASE)
        chars.append(_ALPHABET[rem])
    return "".join(reversed(chars))


def decode(s: str) -> uuid.UUID:
    """Decode a base62 string to a UUID. Raises ValueError on bad input."""
    n = 0
    for c in s:
        if c not in _REVERSE:
            raise ValueError(f"Invalid base62 character: {c!r}")
        n = n * _BASE + _REVERSE[c]
    return uuid.UUID(int=n)


def encode_prefixed(u: uuid.UUID, prefix: str) -> str:
    """Encode a UUID with an entity prefix: ``org_5EfYQ...``."""
    return f"{prefix}_{encode(u)}" if prefix else encode(u)


def decode_prefixed(s: str) -> uuid.UUID:
    """Decode a prefixed short ID to UUID. Also accepts raw UUIDs."""
    m = _PREFIXED_ID_RE.match(s)
    if m and m.group(1) in _ALL_PREFIXES:
        return decode(m.group(2))
    # Might be a raw UUID string — let uuid.UUID handle it
    return uuid.UUID(s)


# ── Prefix registry ──────────────────────────────────────────

_ALL_PREFIXES = frozenset({
    "org", "agent", "user", "link",
    "integ", "tool", "bai", "bat", "file",
})

# Field name → prefix for foreign-key fields in response JSON
_FK_FIELD_PREFIX: dict[str, str] = {
    "org_id": "org",
    "blueprint_agent_id": "agent",
    "end_user_account_id": "user",
    "user_account_id": "user",
    "agent_integration_id": "integ",
    "agent_integration_tool_id": "tool",
    "blueprint_agent_integration_id": "bai",
}

# ── Detection helpers ─────────────────────────────────────────

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I,
)
_PREFIXED_ID_RE = re.compile(r"^([a-z]+)_([0-9A-Za-z]+)$")


def _is_uuid_str(s: str) -> bool:
    return bool(_UUID_RE.match(s))


def _is_prefixed_id(s: str) -> bool:
    m = _PREFIXED_ID_RE.match(s)
    return bool(m and m.group(1) in _ALL_PREFIXES)


# ── Path-based entity prefix for the bare ``id`` field ────────

_ROUTE_WORDS = frozenset({
    "orgs", "agents", "users", "integrations", "tools",
    "files", "read", "grep", "glob", "tree", "mkdir", "mv", "upload", "chat",
    "docs", "swagger",
})


def _id_prefix_from_path(path: str) -> str:
    """Determine the entity prefix for ``id`` based on the request URL."""
    parts = [p for p in path.split("/") if p and p in _ROUTE_WORDS]
    if not parts:
        return ""
    last = parts[-1]
    if last in ("orgs",):
        return "org"
    if last == "agents":
        # /users/{id}/agents → link;  /orgs/{id}/agents → agent
        if len(parts) >= 2 and parts[-2] == "users":
            return "link"
        return "agent"
    if last == "users":
        return "user"
    if last == "integrations":
        # /agents/{id}/integrations → bai
        return "bai"
    if last == "tools":
        return "bat"
    if last in ("files", "read", "grep", "glob", "tree", "mkdir", "mv", "upload"):
        return "file"
    if last == "chat":
        return ""
    return ""


# ── JSON tree walkers ─────────────────────────────────────────

def _encode_response(obj: Any, id_prefix: str) -> Any:
    """Walk response JSON, encoding UUID strings → prefixed short IDs."""
    if isinstance(obj, list):
        return [_encode_response(v, id_prefix) for v in obj]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(v, str) and _is_uuid_str(v):
                prefix = _FK_FIELD_PREFIX.get(k, id_prefix if k == "id" else "")
                out[k] = encode_prefixed(uuid.UUID(v), prefix)
            else:
                out[k] = _encode_response(v, id_prefix)
        return out
    return obj


def _decode_request_body(obj: Any) -> Any:
    """Walk request JSON, decoding prefixed short IDs → UUID strings."""
    if isinstance(obj, str):
        if _is_prefixed_id(obj):
            try:
                return str(decode_prefixed(obj))
            except (ValueError, OverflowError):
                pass
        return obj
    if isinstance(obj, list):
        return [_decode_request_body(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _decode_request_body(v) for k, v in obj.items()}
    return obj


# ── Path segment decoder ─────────────────────────────────────

def _decode_path_segment(seg: str) -> str:
    """Decode a path segment if it's a prefixed short ID or raw UUID."""
    if _is_uuid_str(seg):
        return seg  # already a UUID string, pass through
    if _is_prefixed_id(seg):
        try:
            return str(decode_prefixed(seg))
        except (ValueError, OverflowError):
            pass
    return seg


# ── Middleware ────────────────────────────────────────────────

class ShortIdMiddleware(BaseHTTPMiddleware):
    """Transparently translate between prefixed short IDs and UUIDs."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        # --- Decode path segments ---
        original_path: str = request.scope["path"]
        segments = original_path.split("/")
        request.scope["path"] = "/".join(
            _decode_path_segment(seg) if seg else seg for seg in segments
        )

        # --- Decode query string ---
        qs = request.scope.get("query_string", b"")
        if qs:
            pairs = parse_qsl(qs.decode("utf-8"), keep_blank_values=True)
            decoded_pairs = [(k, _decode_path_segment(v)) for k, v in pairs]
            request.scope["query_string"] = urlencode(decoded_pairs).encode("utf-8")

        # --- Decode JSON request body ---
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        data = _decode_request_body(data)
                        new_body = json.dumps(data).encode("utf-8")

                        # Clear cached body and replace receive
                        request._body = new_body

                        async def _receive():
                            return {
                                "type": "http.request",
                                "body": new_body,
                                "more_body": False,
                            }
                        request._receive = _receive
                    except (json.JSONDecodeError, ValueError):
                        pass

        # Remember the original path for response encoding
        id_prefix = _id_prefix_from_path(original_path)

        # --- Call the actual route ---
        response = await call_next(request)

        # --- Encode UUIDs in JSON response ---
        ct = response.headers.get("content-type", "")
        if ct.startswith("application/json"):
            body_chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                body_chunks.append(
                    chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"),
                )
            raw = b"".join(body_chunks)
            if raw:
                try:
                    data = json.loads(raw)
                    data = _encode_response(data, id_prefix)
                    new_raw = json.dumps(data, default=str).encode("utf-8")
                    headers = {
                        k: v for k, v in response.headers.items()
                        if k.lower() != "content-length"
                    }
                    return Response(
                        content=new_raw,
                        status_code=response.status_code,
                        headers=headers,
                        media_type="application/json",
                    )
                except (json.JSONDecodeError, ValueError):
                    pass

        return response


# ── OpenAPI schema patcher ────────────────────────────────────

# Map path-parameter names → example prefixed short ID
_PARAM_PREFIX: dict[str, str] = {
    "org_id": "org",
    "agent_id": "agent",
    "user_id": "user",
    "blueprint_agent_id": "agent",
    "integration_id": "integ",
    "tool_id": "tool",
}

# Map request/response schema property names → prefix
_PROP_PREFIX: dict[str, str] = {
    **_FK_FIELD_PREFIX,
    "id": "",  # generic — no example prefix
}

_EXAMPLE_UUID = uuid.UUID("a0b1c2d3-e4f5-6789-abcd-ef0123456789")
_EXAMPLE_SHORT = encode(_EXAMPLE_UUID)


def patch_openapi(schema: dict) -> dict:
    """Rewrite UUID references in the OpenAPI schema to show short-ID format."""

    # --- Path parameters ---
    for path_item in (schema.get("paths") or {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters") or []:
                name = param.get("name", "")
                fmt = (param.get("schema") or {}).get("format")
                if fmt == "uuid" and name in _PARAM_PREFIX:
                    prefix = _PARAM_PREFIX[name]
                    param["schema"] = {
                        "type": "string",
                        "example": f"{prefix}_{_EXAMPLE_SHORT}",
                    }

    # --- Request body & response schemas ---
    for comp_name, comp_schema in (schema.get("components", {}).get("schemas") or {}).items():
        props = comp_schema.get("properties") or {}
        for prop_name, prop_def in props.items():
            fmt = prop_def.get("format")
            if fmt == "uuid" or (prop_def.get("type") == "string" and prop_name in _PROP_PREFIX):
                prefix = _PROP_PREFIX.get(prop_name, "")
                if prefix:
                    prop_def.pop("format", None)
                    prop_def["type"] = "string"
                    prop_def["example"] = f"{prefix}_{_EXAMPLE_SHORT}"

    return schema
