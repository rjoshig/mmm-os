"""Pydantic v2 schemas exposing the canonical schema to the Review UI (Phase 6)."""

from __future__ import annotations

from pydantic import BaseModel


class CanonicalFieldRead(BaseModel):
    """A canonical field surfaced to the mapping UI."""

    name: str
    type: str
    required: bool
    kind: str  # "dimension" | "measure"
    taxonomy: str | None = None


class CanonicalFieldsResponse(BaseModel):
    """The canonical fields a source column may map to."""

    version: int
    fields: list[CanonicalFieldRead]
    min_measures_required: int
