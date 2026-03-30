"""Pydantic models for org API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateOrgRequest(BaseModel):
    display_name: str = ""
    timezone: str = "UTC"
    metadata: dict = Field(default_factory=dict)


class UpdateOrgRequest(BaseModel):
    display_name: str | None = None
    timezone: str | None = None
    metadata: dict | None = None


class OrgSummary(BaseModel):
    id: str
    display_name: str
    created_at: datetime


class OrgDetail(BaseModel):
    id: str
    display_name: str
    timezone: str
    metadata: dict
    created_at: datetime
    updated_at: datetime
