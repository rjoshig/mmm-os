"""Config-driven I/O profile (Phase 14, CC-14).

A versioned-as-data record of the logical storage roots the file/output lifecycle
uses — ``input`` / ``output`` / ``temp`` / ``archive`` / ``error`` / ``reject``.
A row with ``tenant_id`` NULL is the **global default**; a per-tenant row
overrides individual roots. Values are storage key prefixes resolved through the
``ObjectStorage`` abstraction (ADR-006, ADR-011) — never a hardcoded dialect/host.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class IoProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-tenant (or global-default) I/O path configuration (CC-14).

    Not ``TenantScopedMixin``: ``tenant_id`` is nullable so a single row with
    ``tenant_id IS NULL`` can hold the global default. A per-tenant row overrides
    only the roots it sets; unset roots fall back to the global default, then the
    env defaults in ``Settings``.
    """

    __tablename__ = "io_profile"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tenant.id", ondelete="CASCADE"), index=True
    )
    input_path: Mapped[str | None] = mapped_column(String(1024))
    output_path: Mapped[str | None] = mapped_column(String(1024))
    temp_path: Mapped[str | None] = mapped_column(String(1024))
    archive_path: Mapped[str | None] = mapped_column(String(1024))
    error_path: Mapped[str | None] = mapped_column(String(1024))
    reject_path: Mapped[str | None] = mapped_column(String(1024))
