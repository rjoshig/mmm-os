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
    # Credential status (Slice 7.3). The token itself is never returned — only
    # whether one is stored (in the SecretStore, CC-10) and its metadata.
    has_credential: bool = False
    credential_scopes: list[str] | None = None
    credential_expires_at: datetime | None = None


class ConnectorCredentialInput(BaseModel):
    """A partner credential/token to store for a connector (Slice 7.3).

    The token is written to the ``SecretStore`` (encrypted, never logged, CC-10/
    CC-12); the database keeps only a reference + metadata.
    """

    token: str = Field(min_length=1, description="Partner API token / OAuth access token.")
    scopes: list[str] | None = None
    expires_at: datetime | None = None


class ConnectorCredentialStatus(BaseModel):
    """Non-secret status of a connector's stored credential."""

    has_credential: bool
    scopes: list[str] | None = None
    expires_at: datetime | None = None


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


class SyncRunListItem(BaseModel):
    """A sync run enriched with its connector's key + name (tenant-wide runs view)."""

    run: SyncRunRead
    connector_key: str
    connector_name: str
    triggered_by_email: str | None = None


class ScheduleUpdate(BaseModel):
    """Set or clear a connector's automatic schedule (Cycle 3)."""

    interval_minutes: int | None = Field(
        default=None, description="Run every N minutes; null/0 disables the schedule."
    )


class RunDueResponse(BaseModel):
    """Result of running due syncs on demand: the runs that fired."""

    ran: list[SyncRunRead]
