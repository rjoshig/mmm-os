"""Pydantic v2 schemas for the AI suggestion API (05.2)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class SuggestionRead(BaseModel):
    """A stored suggestion as returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    confidence: float | None
    rationale: str | None
    state: str


class SuggestMappingResponse(BaseModel):
    """Suggestions returned for a sheet's columns."""

    suggestions: list[SuggestionRead]


class AcceptResponse(BaseModel):
    """Result of accepting a suggestion."""

    suggestion: SuggestionRead
    mapping_config_version: int | None


class LlmUsageRead(BaseModel):
    """A tenant's LLM usage over the last 24h vs its caps (05.1, CC-13)."""

    calls: int
    tokens: int
    call_cap: int
    token_cap: int
    over_budget: bool
