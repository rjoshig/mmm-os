"""Pydantic v2 schemas for the governance/admin API (Phase 8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    """A tenant user as shown in the admin user list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    status: str


class AuditEntryRead(BaseModel):
    """An audit-log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: dict[str, Any] | None
    created_at: datetime


class AccessReviewRow(BaseModel):
    """A user + effective permissions row for an access review (Phase 08.1)."""

    user_id: uuid.UUID
    email: str
    role: str
    permissions: list[str]
