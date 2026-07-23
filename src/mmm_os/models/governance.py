"""Governance models: the audit log (Phase 8, P8-2 / CC-3, CC-7)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """An append-only record of a sensitive action (who / what / when).

    Config changes, approvals, overrides, logins, and data exports are recorded
    here for traceability + compliance (P8-2, extended in Phase 08.1). Never
    stores secret values (CC-12).
    """

    __tablename__ = "audit_log"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON)
