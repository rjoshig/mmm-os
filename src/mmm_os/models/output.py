"""Clean canonical output rows with full traceability (CC-3, ADR-005).

For v1 this is a table in the backend database (no separate warehouse). Each row
traces to its source file + sheet + row and the config/rule-set versions applied.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OutputRow(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A single clean, canonically-keyed output row plus traceability metadata."""

    __tablename__ = "output_row"

    # Traceability (CC-3): where this row came from and which config produced it.
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("file.id", ondelete="SET NULL"), index=True
    )
    source_sheet: Mapped[str | None] = mapped_column(String(255))
    source_row: Mapped[int | None] = mapped_column(Integer)
    mapping_config_version: Mapped[int | None] = mapped_column(Integer)
    rule_set_version: Mapped[int | None] = mapped_column(Integer)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # The canonical row payload (dimensions + measures + metadata), keyed by
    # canonical field name. Kept as JSON so the canonical schema stays config-driven.
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
