"""Pydantic models for org API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    display_name: str = ""
    timezone: str = "UTC"
    metadata: dict = Field(default_factory=dict)


class UpdateOrgRequest(BaseModel):
    display_name: str | None = None
    timezone: str | None = None
    metadata: dict | None = None
    enabled_integration_slugs: List[str] | None = None


class AddOrgIntegrationRequest(BaseModel):
    slug: str


# ── Responses ─────────────────────────────────────────────────

class OrgSummaryResponse(BaseModel):
    id: str
    display_name: str
    created_at: datetime


class OrgDetailResponse(BaseModel):
    id: str
    display_name: str
    timezone: str
    metadata: dict
    enabled_integration_slugs: List[str]
    created_at: datetime
    updated_at: datetime
