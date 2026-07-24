"""First-class Stack: the model-ready Gold panel (Phase 16, ADR-012, ADR-014).

A ``Stack`` is a named, versioned, publishable dataset assembled from one or more
cleaned per-source (Silver) outputs and harmonized across sources. ``StackRow``
holds the canonical panel rows with full lineage back to the source file (CC-3).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Stack(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A named, versioned, model-ready dataset (the Gold panel)."""

    __tablename__ = "stack"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lifecycle_status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    grain: Mapped[str | None] = mapped_column(String(16))  # daily | weekly | monthly
    reporting_currency: Mapped[str | None] = mapped_column(String(3))
    reporting_timezone: Mapped[str | None] = mapped_column(String(64))
    # Snapshot of the export contract (columns present) at assembly time.
    schema_contract: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # The Silver source outputs (job ids) this stack was assembled from.
    source_job_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL")
    )
    cloned_from: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class StackRow(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A single canonical row of a Stack panel, with lineage to its source (CC-3)."""

    __tablename__ = "stack_row"

    stack_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("stack.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stack_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Lineage back through the Silver output to the Bronze file.
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    source_sheet: Mapped[str | None] = mapped_column(String(255))
    source_row: Mapped[int | None] = mapped_column(Integer)
    # The canonical panel row (dimensions + measures + factors + extensions), JSON.
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
