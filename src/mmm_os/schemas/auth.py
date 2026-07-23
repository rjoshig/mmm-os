"""Pydantic v2 schemas for the auth API (Phase 00.5)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials for a password login."""

    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class PrincipalRead(BaseModel):
    """The authenticated identity returned to the client."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str


class LoginResponse(BaseModel):
    """Result of a successful login: a bearer token + the principal."""

    token: str
    principal: PrincipalRead
