"""Pydantic v2 schemas for the validation API (04.2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidateRequest(BaseModel):
    """Request to validate records for a job."""

    rows: list[dict[str, Any]]
    anomaly_measure: str | None = None
    group_by: str | None = None
    policy_overrides: dict[str, str] | None = None


class FlagRead(BaseModel):
    """A validation flag as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    severity: str
    description: str
    location: dict[str, Any]
    review_status: str
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None


class ValidateResponse(BaseModel):
    """Result of running validation for a job."""

    blocked: bool
    flags: list[FlagRead]


class ReviewRequest(BaseModel):
    """Request to record a review decision on a flag."""

    status: str = Field(description="acknowledged | resolved | overridden")
    resolved_by: uuid.UUID | None = None
