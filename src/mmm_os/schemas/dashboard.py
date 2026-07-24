"""Schemas for the tenant dashboard + live monitoring (Phase 20)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    """Tenant-level operational KPIs."""

    files_total: int
    jobs_by_status: dict[str, int]
    active_jobs: int
    stacks_total: int
    stacks_published: int
    open_flags_by_severity: dict[str, int]
    sync_by_status: dict[str, int]


class ActiveJobRead(BaseModel):
    """An in-flight job for live monitoring (poll target)."""

    id: uuid.UUID
    file_id: uuid.UUID | None
    status: str
    started_at: datetime | None
    created_at: datetime


class ActiveJobsResponse(BaseModel):
    """The tenant's currently in-flight jobs."""

    active: list[ActiveJobRead]
