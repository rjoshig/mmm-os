"""Tenant-authored validation rules (Part 3 — first-class custom semantic checks).

A named, enable-able, severity-carrying sandboxed expression (e.g.
``clicks <= impressions``) that runs everywhere validation runs — pipeline, sheet
validation, and the Stack publish gate (CC-15). Config-as-data (CC-4),
tenant-scoped (CC-1). Expressions run only in the AST sandbox (ADR-004).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.enums import Severity
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ValidationRule(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A tenant's custom, sandboxed validation rule."""

    __tablename__ = "validation_rule"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_validation_rule_name"),)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default=Severity.WARNING.value
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL")
    )
