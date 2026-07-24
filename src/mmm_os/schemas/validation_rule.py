"""Schemas for first-class custom validation rules (Part 3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ValidationRuleCreate(BaseModel):
    """Create a validation rule."""

    name: str
    expression: str
    severity: str = "warning"
    enabled: bool = True
    description: str | None = None


class ValidationRuleUpdate(BaseModel):
    """Partial update of a validation rule (only provided fields change)."""

    name: str | None = None
    expression: str | None = None
    severity: str | None = None
    enabled: bool | None = None
    description: str | None = None


class ValidationRuleRead(BaseModel):
    """A persisted validation rule."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    expression: str
    severity: str
    enabled: bool
    description: str | None
    created_at: datetime
