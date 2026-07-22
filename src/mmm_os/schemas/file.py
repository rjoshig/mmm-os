"""Pydantic v2 schemas for file/job read payloads and the ingest response."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


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


class IngestResponse(BaseModel):
    """Response returned after a successful upload."""

    file: FileRead
    job: JobRead


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


class ProcessResponse(BaseModel):
    """Response returned after processing (structure detection) a file."""

    job: JobRead
    sheets: list[SheetRead]
