"""Pydantic v2 schemas for the mapping API (02.2)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mmm_os.models.enums import RuleLayer


class SaveMappingRequest(BaseModel):
    """Request body to save (version) a sheet's mapping."""

    name: str = Field(min_length=1, max_length=255)
    layer: str = RuleLayer.CUSTOMER.value
    mapping: dict[str, str | None]


class MappedColumnRead(BaseModel):
    """A source column mapped to a canonical field."""

    source_name: str
    canonical_field: str


class MappingValidation(BaseModel):
    """Validation summary of applying a mapping to a sheet's columns."""

    mapped: list[MappedColumnRead]
    ignored: list[str]
    invalid: list[str]
    missing_required: list[str]
    is_complete: bool


class MappingConfigRead(BaseModel):
    """A saved mapping config as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    file_signature: str
    version: int
    layer: str
    mapping: dict[str, Any]


class SaveMappingResponse(BaseModel):
    """Response after saving a mapping."""

    config: MappingConfigRead
    validation: MappingValidation


class AutoMapResponse(BaseModel):
    """Response after attempting to auto-map a sheet."""

    signature: str
    matched: bool
    mapping: dict[str, str | None]
    validation: MappingValidation | None
