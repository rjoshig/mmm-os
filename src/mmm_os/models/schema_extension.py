"""Tenant-scoped schema extensions (Phase 21, ADR-015).

A metadata registry that lets a tenant add its own dimensions / measures / factors
on top of the fixed canonical core — without a migration, because extension
*values* live in the existing JSON columns (``output_row.data`` / ``stack_row``).
Config-as-data (CC-4), tenant-isolated (CC-1). An optional ``validation`` holds a
sandboxed boolean expression (ADR-004) evaluated as a custom check.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SchemaExtension(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A custom dimension/measure/factor a tenant adds to the canonical schema."""

    __tablename__ = "schema_extension"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_schema_extension_name"),)

    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # dimension|measure|factor
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(16), nullable=False, default="string")
    taxonomy_ref: Mapped[str | None] = mapped_column(String(128))
    # Optional sandboxed boolean expression run as a custom validation check.
    validation: Mapped[str | None] = mapped_column(Text)
    layer: Mapped[str] = mapped_column(String(16), nullable=False, default="customer")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lifecycle_status: Mapped[str] = mapped_column(String(16), nullable=False, default="published")
