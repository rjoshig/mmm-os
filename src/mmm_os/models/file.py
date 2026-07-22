"""File, sheet, and profile models (Phase 1 will populate these)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.enums import SheetStatus
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class File(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A raw uploaded file: immutable bytes (CC-2) plus metadata + storage pointer."""

    __tablename__ = "file"

    filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    storage_uri: Mapped[str | None] = mapped_column(String(2048))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))


class Sheet(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A sheet within a file; records the detected header location and status."""

    __tablename__ = "sheet"

    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("file.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_name: Mapped[str | None] = mapped_column(String(255))
    sheet_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    header_row_index: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SheetStatus.DETECTED.value
    )


class Profile(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Per-sheet column stats / distinct values / samples — the AI input (Phase 5)."""

    __tablename__ = "profile"
    __table_args__ = (UniqueConstraint("sheet_id"),)

    sheet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sheet.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_count: Mapped[int | None] = mapped_column(Integer)
    column_stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
