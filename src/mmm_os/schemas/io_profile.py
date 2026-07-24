"""Schemas for the config-driven I/O profile (Phase 14, CC-14)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IoProfileUpdate(BaseModel):
    """Update payload for a tenant's I/O profile (only provided roots are set)."""

    input_path: str | None = None
    output_path: str | None = None
    temp_path: str | None = None
    archive_path: str | None = None
    error_path: str | None = None
    reject_path: str | None = None


class IoProfileRead(BaseModel):
    """The effective (resolved) logical roots for a tenant."""

    model_config = ConfigDict(from_attributes=True)

    input: str
    output: str
    temp: str
    archive: str
    error: str
    reject: str


class ExportToDestinationResponse(BaseModel):
    """Result of writing a job's output to the configured destination."""

    job_id: str
    written_key: str | None
    row_count: int
