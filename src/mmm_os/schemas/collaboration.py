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


class CommentCreate(BaseModel):
    """Request to post a comment on an object, optionally @mentioning teammates."""

    target_type: str = Field(pattern="^(file|sheet|flag)$")
    target_id: uuid.UUID
    body: str = Field(min_length=1, max_length=4000)
    mentions: list[uuid.UUID] = Field(default_factory=list)


class CommentRead(BaseModel):
    """A comment as returned to the UI (author email resolved)."""

    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    author_user_id: uuid.UUID | None
    author_email: str | None
    body: str
    created_at: datetime


class NotificationRead(BaseModel):
    """An in-app notification for the current user."""

    id: uuid.UUID
    kind: str
    target_type: str | None
    target_id: uuid.UUID | None
    message: str
    read: bool
    created_at: datetime
