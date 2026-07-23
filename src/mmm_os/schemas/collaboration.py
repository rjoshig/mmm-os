"""Schemas for collaboration: work assignment / review queue (Phase 13.4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    """Request to assign a unit of review work to a tenant user."""

    target_type: str = Field(pattern="^(file|sheet)$")
    target_id: uuid.UUID
    assignee_user_id: uuid.UUID
    note: str | None = Field(default=None, max_length=500)


class AssignmentRead(BaseModel):
    """An assignment as returned to the UI (assignee email resolved for display)."""

    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    assignee_user_id: uuid.UUID
    assignee_email: str | None
    assigned_by: uuid.UUID | None
    status: str
    note: str | None
    created_at: datetime
