"""Schemas for RBAC role management (Phase 19)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class RoleMatrixResponse(BaseModel):
    """The role → permission matrix (deny-by-default)."""

    roles: dict[str, list[str]]


class UserRoleRead(BaseModel):
    """A tenant user and its role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    status: str


class SetRoleRequest(BaseModel):
    """Assign a role to a user."""

    role: str
