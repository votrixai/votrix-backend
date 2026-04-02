"""Pydantic models for end user account API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreateEndUserAccountRequest(BaseModel):
    display_name: str = ""
    sandbox: bool = False


class UpdateEndUserAccountRequest(BaseModel):
    display_name: Optional[str] = None
    sandbox: Optional[bool] = None


class EndUserAccountSummary(BaseModel):
    id: str
    display_name: str
    sandbox: bool
    created_at: datetime


class EndUserAccountDetail(BaseModel):
    id: str
    org_id: str
    display_name: str
    sandbox: bool
    created_at: datetime
    updated_at: datetime


class CreateEndUserAgentRequest(BaseModel):
    blueprint_agent_id: str


class EndUserAgentDetail(BaseModel):
    id: str
    end_user_account_id: str
    blueprint_agent_id: str
    created_at: datetime
