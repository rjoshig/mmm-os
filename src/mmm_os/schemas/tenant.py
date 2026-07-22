"""Pydantic v2 schemas for tenant and user create/read payloads.

Kept separate from the ORM models (``models/``) per CODING_STANDARDS.md. ``Read``
schemas use ``from_attributes`` so they can be built directly from ORM instances.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    """Payload to create a tenant."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)


class TenantRead(BaseModel):
    """A tenant as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class UserCreate(BaseModel):
    """Payload to create a user scoped to a tenant."""

    tenant_id: uuid.UUID
    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=255)
    role: str = Field(default="member", max_length=50)


class UserRead(BaseModel):
    """A user as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    display_name: str | None
    role: str
