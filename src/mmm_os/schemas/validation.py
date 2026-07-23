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


class BulkReviewRequest(BaseModel):
    """Request to apply one review decision to many flags at once (a cluster).

    Callers pass explicit flag ids (the UI groups flags into clusters by
    ``location.check`` + field), so the endpoint stays dialect-agnostic — no
    JSON-column filtering — and the client controls the grouping.
    """

    flag_ids: list[uuid.UUID] = Field(min_length=1)
    status: str = Field(description="acknowledged | resolved | overridden")
    resolved_by: uuid.UUID | None = None


class BulkReviewResponse(BaseModel):
    """Result of a bulk review: the updated flags (only those found for the job)."""

    updated: list[FlagRead]
