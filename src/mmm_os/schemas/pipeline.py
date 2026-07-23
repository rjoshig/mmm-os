"""Pydantic v2 schemas for the full-pipeline API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class SheetPipelineRead(BaseModel):
    """Per-sheet outcome of a pipeline run."""

    sheet_id: uuid.UUID
    sheet_name: str | None
    needs_mapping: bool
    mapping_config_version: int | None
    missing_required: list[str]
    flag_count: int
    blocked: bool
    output_rows_written: int | None
    rule_set_version: int | None


class PipelineRunResponse(BaseModel):
    """Aggregate outcome of running the full pipeline over a file."""

    file_id: uuid.UUID
    job_id: uuid.UUID
    rows_written: int
    sheets: list[SheetPipelineRead]


class SheetPipelineStatus(BaseModel):
    """Per-sheet pipeline stage for the Review UI stepper."""

    sheet_id: uuid.UUID
    sheet_name: str | None
    has_mapping: bool
    has_rule_set: bool


class FilePipelineStatus(BaseModel):
    """Per-file pipeline stage summary (drives the file-detail stepper).

    Validation/output are file-(job-)level today; mapping/rules are per sheet.
    """

    file_id: uuid.UUID
    validated: bool
    blocking_open: int
    has_output: bool
    sheets: list[SheetPipelineStatus]
