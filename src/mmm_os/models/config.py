"""Config-as-data models: mapping configs, taxonomies, and rule sets/rules.

All are **versioned** (CC-4) and layered (global/template/customer). Stored as
data, never code.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.enums import RuleLayer
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class MappingConfig(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A saved column→canonical mapping, keyed by tenant + file signature. Versioned."""

    __tablename__ = "mapping_config"
    __table_args__ = (UniqueConstraint("tenant_id", "file_signature", "version"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_signature: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, default=RuleLayer.CUSTOMER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Taxonomy(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A controlled vocabulary (channel, funnel_stage, …). Versioned."""

    __tablename__ = "taxonomy"
    __table_args__ = (UniqueConstraint("tenant_id", "name", "version"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class TaxonomyAlias(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A synonym mapping a raw value to a canonical taxonomy term."""

    __tablename__ = "taxonomy_alias"

    taxonomy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("taxonomy.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_term: Mapped[str] = mapped_column(String(512), nullable=False)


class RuleSet(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """An ordered, versioned, layered set of transformation rules (CC-4)."""

    __tablename__ = "rule_set"
    __table_args__ = (UniqueConstraint("tenant_id", "name", "version"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, default=RuleLayer.CUSTOMER.value)


class Rule(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A single declarative transformation rule (Appendix D)."""

    __tablename__ = "rule"

    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("rule_set.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_field: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    condition: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, default=RuleLayer.CUSTOMER.value)
