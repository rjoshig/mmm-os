"""Schemas for tenant schema extensions (Phase 21, ADR-015)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class SchemaExtensionCreate(BaseModel):
    """Register a custom dimension/measure/factor."""

    kind: str  # dimension | measure | factor
    name: str
    data_type: str = "string"
    taxonomy_ref: str | None = None
    validation: str | None = None


class SchemaExtensionRead(BaseModel):
    """A persisted schema extension."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    name: str
    data_type: str
    taxonomy_ref: str | None
    validation: str | None
    layer: str
    version: int
    lifecycle_status: str


class ResolvedFieldRead(BaseModel):
    """A field in the resolved schema (core or extension)."""

    name: str
    kind: str
    type: str
    source: str  # core | extension


class ResolvedSchemaResponse(BaseModel):
    """The resolved schema: canonical core + this tenant's extensions."""

    fields: list[ResolvedFieldRead]
