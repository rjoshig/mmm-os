"""Pydantic schemas for per-customer feed templates (Slice 7.4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FixedField(BaseModel):
    """One fixed-width column: name + zero-based start offset + width."""

    name: str = Field(min_length=1, max_length=255)
    start: int = Field(ge=0)
    width: int = Field(ge=1)


class FeedTemplateCreate(BaseModel):
    """Request to define a customer's feed template (a reusable file layout)."""

    name: str = Field(min_length=1, max_length=255)
    fmt: str = Field(default="delimited", pattern="^(delimited|fixed_width|xlsx)$")
    delimiter: str | None = Field(default=None, max_length=4)
    has_header: bool = True
    fixed_fields: list[FixedField] = Field(default_factory=list)
    expected_columns: list[str] = Field(default_factory=list)
    filename_glob: str | None = Field(default=None, max_length=255)


class FeedTemplateRead(BaseModel):
    """A stored feed template."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    fmt: str
    delimiter: str | None
    has_header: bool
    fixed_fields: list[FixedField]
    expected_columns: list[str]
    filename_glob: str | None
    created_at: datetime


class FeedTemplatePreview(BaseModel):
    """A bounded parse of a sample file using a template's layout."""

    columns: list[str]
    rows: list[list[str | None]]
    row_count: int
    signature_matches: bool | None = None
