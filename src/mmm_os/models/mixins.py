"""Reusable declarative mixins for portable, multi-tenant ORM models.

All models use dialect-agnostic types (``Uuid`` PKs, UTC ``DateTime(timezone=True)``)
so the database swaps SQLite→Postgres by config only (see CODING_STANDARDS.md).
Every tenant-scoped table mixes in ``TenantScopedMixin`` to satisfy CC-1.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key (portable: CHAR on SQLite, UUID on Postgres)."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Adds UTC ``created_at`` / ``updated_at`` timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class TenantScopedMixin:
    """Adds a non-null ``tenant_id`` FK to ``tenant.id`` (CC-1).

    Declarative mixins copy this column onto every subclass, so every
    tenant-scoped table carries the same isolation key.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
