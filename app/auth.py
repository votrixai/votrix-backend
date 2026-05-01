"""Supabase JWT verification and FastAPI dependency.

Uses asymmetric signing keys (ES256/RS256) via Supabase's JWKS endpoint.
The JWKS client caches keys and handles rotation (current + standby) automatically.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.engine import get_session
from app.db.queries.workspaces import get_member_role, get_user_workspaces, is_member

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthedUser:
    id: uuid.UUID
    email: str | None = None


@dataclass(frozen=True)
class WorkspaceContext:
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: str


@lru_cache
def _jwks_client() -> PyJWKClient:
    s = get_settings()
    if not s.supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")
    return PyJWKClient(f"{s.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def _verify(token: str) -> dict:
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            options={"require": ["exp", "sub", "aud"]},
            leeway=30,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid audience")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


_PREVIEW_API_KEY = "preview-dev-votrix-2025"


def require_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_preview_key: str | None = Header(None, alias="x-preview-key"),
    x_preview_user_id: str | None = Header(None, alias="x-preview-user-id"),
) -> AuthedUser:
    # Preview mode: hardcoded key + explicit user-id header
    if x_preview_key is not None:
        if x_preview_key != _PREVIEW_API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid preview key")
        if not x_preview_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Preview-User-Id header required")
        try:
            return AuthedUser(id=uuid.UUID(x_preview_user_id))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid preview user ID")

    # Standard JWT auth
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    claims = _verify(creds.credentials)
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sub claim")
    return AuthedUser(id=user_id, email=claims.get("email"))


async def require_workspace(
    user: AuthedUser = Depends(require_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-Id"),
    db: AsyncSession = Depends(get_session),
) -> WorkspaceContext:
    if x_workspace_id is not None:
        try:
            workspace_id = uuid.UUID(x_workspace_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Workspace-Id must be a valid UUID",
            )
        if not await is_member(db, workspace_id, user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )
        role = await get_member_role(db, workspace_id, user.id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )
        return WorkspaceContext(user_id=user.id, workspace_id=workspace_id, role=role)

    workspaces = await get_user_workspaces(db, user.id)
    if len(workspaces) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-Id header required",
        )
    workspace, role = workspaces[0]
    return WorkspaceContext(user_id=user.id, workspace_id=workspace.id, role=role)
