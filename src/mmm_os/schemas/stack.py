"""Schemas for the Stage-2 Stack API (Phase 16)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from mmm_os.schemas.output import MeasureStatsRead


class HarmonizationSpecIn(BaseModel):
    """Cross-source harmonization spec (config-as-data)."""

    field_map: dict[str, str] = {}
    value_map: dict[str, dict[str, str]] = {}


class StackCreate(BaseModel):
    """Create (assemble) a draft Stack from Silver outputs."""

    name: str
    description: str | None = None
    source_job_ids: list[uuid.UUID]
    harmonization: HarmonizationSpecIn = HarmonizationSpecIn()
    grain: str | None = None


class StackRead(BaseModel):
    """A Stack's metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    version: int
    lifecycle_status: str
    grain: str | None
    reporting_currency: str | None
    reporting_timezone: str | None
    schema_contract: dict[str, Any]
    source_job_ids: list[str]
    cloned_from: uuid.UUID | None
    created_at: datetime


class StackDetail(StackRead):
    """A Stack plus row count and per-measure statistics."""

    row_count: int
    measures: list[MeasureStatsRead]


class PublishStackResponse(BaseModel):
    """Result of a publish attempt: published, or blocked with panel flags."""

    stack_id: uuid.UUID
    lifecycle_status: str
    published: bool
    blocking_flags: list[dict[str, Any]]


class HarmonizationSuggestion(BaseModel):
    """A proposed value harmonization (raw -> canonical), for human ratification."""

    raw: str
    canonical: str


class HarmonizationSuggestionsResponse(BaseModel):
    """Deterministic harmonization suggestions for a set of source outputs."""

    field: str
    suggestions: list[HarmonizationSuggestion]
