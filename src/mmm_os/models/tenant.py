"""Tenant and user models — the root of tenant isolation (ADR-003)."""

from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer organisation — the isolation root.

    The ``tenant`` table is intentionally not tenant-scoped: it *is* the tenant.
    Every other domain table carries ``tenant_id`` referencing this table.
    """

    __tablename__ = "tenant"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class User(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A user belonging to a tenant. Roles/RBAC are enforced in Phase 8."""

    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
