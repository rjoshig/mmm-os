"""Partner-connector entities (Phase 9, CC-9/CC-10).

The connector *catalog* is an in-code registry (`connectors.registry`); the
tenant-scoped runtime entities are here. Credentials store only a **reference** to
the secret in the ``SecretStore`` — never the token value (CC-10).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.enums import JobStatus
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ConnectorConfig(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Per-tenant configuration for one partner connector."""

    __tablename__ = "connector_config"

    connector_key: Mapped[str] = mapped_column(String(32), nullable=False)  # meta/google_ads/…
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # metrics/dimensions/currency/timezone/lookback_days/backfill_days/schedule.
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Provenance when this config was created by cloning another (Phase 15).
    # A clone never copies the ConnectorCredential/secret (CC-10) — it starts
    # unauthenticated.
    cloned_from: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class ConnectorCredential(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A reference to a connector's encrypted token in the SecretStore (CC-10)."""

    __tablename__ = "connector_credential"
    __table_args__ = (UniqueConstraint("connector_config_id"),)

    connector_config_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("connector_config.id", ondelete="CASCADE"), nullable=False, index=True
    )
    secret_ref_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str] | None] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncRun(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """One connector pull over a date window (observability + traceability, CC-3/CC-7)."""

    __tablename__ = "sync_run"

    connector_config_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("connector_config.id", ondelete="CASCADE"), nullable=False, index=True
    )
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.PENDING.value)
    # Who triggered this sync (Cycle 6); nullable for scheduled/system runs.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL")
    )
    row_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
