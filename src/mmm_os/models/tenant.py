"""Tenant and user models — the root of tenant isolation (ADR-003)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String, UniqueConstraint
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


class TenantSettings(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Per-tenant reporting context for MMM normalization (Cycle 2).

    One row per tenant (unique ``tenant_id``). Config-as-data (CC-4): the reporting
    currency + timezone and the FX rate table drive currency/timezone normalization
    so every tenant's output lands in one consistent reporting frame.
    """

    __tablename__ = "tenant_settings"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_settings_tenant"),)

    reporting_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    reporting_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    # {source_currency (ISO): rate to multiply a value in that currency into the
    # reporting currency}. The reporting currency itself is implicitly 1.0.
    fx_rates: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class User(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A user belonging to a tenant. Auth lands in Phase 00.5; RBAC in Phase 8."""

    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")

    # Authentication (Phase 00.5). Password is stored as a PBKDF2 hash + salt;
    # the plaintext is never persisted. Nullable so pre-auth rows remain valid.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_salt: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
