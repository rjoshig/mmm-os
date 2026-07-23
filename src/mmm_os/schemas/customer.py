"""Schemas for customer/workspace management (Cycle 7)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerRead(BaseModel):
    """A customer / workspace (the tenant) as returned to the management UI."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    tier: str
    region: str
    status: str
    created_at: datetime


class CustomerCreate(BaseModel):
    """Request to onboard a new customer / workspace."""

    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    tier: str = Field(default="standard", pattern="^(standard|enterprise)$")
    region: str = Field(default="us", max_length=32)
