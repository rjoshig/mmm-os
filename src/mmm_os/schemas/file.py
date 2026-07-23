"""Pydantic v2 schemas for file/job read payloads and the ingest response."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FileRead(BaseModel):
    """A stored file as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    filename: str
    content_type: str | None
    byte_size: int | None
    checksum_sha256: str | None
    storage_uri: str | None
    created_at: datetime


class JobRead(BaseModel):
    """A processing job as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    file_id: uuid.UUID | None
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    created_by: uuid.UUID | None = None


class JobListItem(BaseModel):
    """A job enriched with filename + actor email for the Runs table (Cycle 6)."""

    job: JobRead
    filename: str | None
    triggered_by_email: str | None


class JobEventRead(BaseModel):
    """A per-stage status/timing record for a job (observability, CC-7)."""

    model_config = ConfigDict(from_attributes=True)

    stage: str
    status: str
    message: str | None
    duration_ms: int | None
    created_at: datetime


class JobDetail(BaseModel):
    """A job with its filename and ordered stage events (the Runs drill-in)."""

    job: JobRead
    filename: str | None
    events: list[JobEventRead]


class IngestResponse(BaseModel):
    """Response returned after a successful upload."""

    file: FileRead
    job: JobRead


class IngestByPathRequest(BaseModel):
    """Request to ingest a file by server-side path (landing zone, Phase 01.4)."""

    path: str = Field(min_length=1, description="Path within an allowlisted landing root.")


class SheetRead(BaseModel):
    """A detected sheet as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    sheet_name: str | None
    sheet_index: int
    header_row_index: int | None
    status: str
    columns: list[dict[str, Any]]


class SheetAutoMap(BaseModel):
    """Auto-map status for one processed sheet (Slice 7.7)."""

    sheet_id: uuid.UUID
    signature: str
    auto_mapped: bool
    is_complete: bool
    missing_required: list[str]


class ProcessResponse(BaseModel):
    """Response returned after processing (structure detection) a file."""

    job: JobRead
    sheets: list[SheetRead]
    # The feed template whose filename glob drove parsing, if any (Slice 7.7).
    matched_template: str | None = None
    # Per-sheet auto-map status: whether a saved mapping already applies by signature.
    auto_map: list[SheetAutoMap] = []


class FileListItem(BaseModel):
    """A file summarised for the dashboard list (P6-1)."""

    file: FileRead
    latest_job_status: str | None
    sheet_count: int
    needs_review_sheets: int


class FileDetail(BaseModel):
    """A file with its detected sheets and latest job (drill-in view)."""

    file: FileRead
    latest_job: JobRead | None
    sheets: list[SheetRead]


class ProfileRead(BaseModel):
    """A sheet's profile (per-column stats) as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sheet_id: uuid.UUID
    row_count: int | None
    column_stats: dict[str, Any]


class SheetDetail(BaseModel):
    """A sheet with its profile (mapping-review input)."""

    sheet: SheetRead
    profile: ProfileRead | None


class SheetRowsResponse(BaseModel):
    """A bounded sample of a sheet's real data rows (transform/validation input)."""

    columns: list[str]
    rows: list[dict[str, Any]]


class BatchResponse(BaseModel):
    """Aggregate result of enqueuing + draining a batch of files (Phase 7)."""

    enqueued: int
    processed: int
    retried: int
    dead_lettered: int
