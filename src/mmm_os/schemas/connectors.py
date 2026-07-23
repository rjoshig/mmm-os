"""Pydantic v2 schemas for the connector API (Phase 9)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConnectorConfigCreate(BaseModel):
    """Request to create a per-tenant connector configuration."""

    connector_key: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    account_ids: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ConnectorConfigRead(BaseModel):
    """A stored connector configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    connector_key: str
    name: str
    account_ids: list[str]
    settings: dict[str, Any]
    enabled: bool


class SyncRunRead(BaseModel):
    """A connector sync run."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connector_config_id: uuid.UUID
    window_start: date
    window_end: date
    status: str
    row_count: int | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
