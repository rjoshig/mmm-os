"""Pydantic v2 schemas for the output-generation API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class GenerateOutputResponse(BaseModel):
    """Result of generating clean output for a job/sheet."""

    job_id: uuid.UUID
    file_id: uuid.UUID
    sheet_id: uuid.UUID
    rows_written: int
    mapping_config_version: int | None
    rule_set_version: int | None


class OutputRowRead(BaseModel):
    """A persisted clean output row with traceability metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_file_id: uuid.UUID | None
    source_sheet: str | None
    source_row: int | None
    mapping_config_version: int | None
    rule_set_version: int | None
    ingested_at: datetime | None
    data: dict[str, Any]


class OutputListResponse(BaseModel):
    """The clean output rows generated for a job."""

    file_id: uuid.UUID
    filename: str
    rows: list[OutputRowRead]


class ContractField(BaseModel):
    """One column in the MMM export contract."""

    name: str
    type: str
    kind: str  # dimension | measure | factor


class OutputContract(BaseModel):
    """The "Export to MMM" contract: the schema + shape a modeler will receive."""

    file_id: uuid.UUID
    filename: str
    row_count: int
    columns: list[ContractField]
    mapping_config_version: int | None
    rule_set_version: int | None
    sample: list[dict[str, Any]]


class LineageSource(BaseModel):
    """One source sheet contributing to a job's clean output."""

    source_sheet: str | None
    row_count: int


class OutputLineage(BaseModel):
    """Provenance of a job's clean output: source → config versions → output (CC-3)."""

    file_id: uuid.UUID
    filename: str
    output_row_count: int
    mapping_config_version: int | None
    rule_set_version: int | None
    sources: list[LineageSource]
