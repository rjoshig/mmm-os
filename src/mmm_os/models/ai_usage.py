"""LLM usage ledger + per-tenant budget models (Phase 05.1, CC-13)."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class LlmUsage(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """One metered LLM call: tokens attributed to a tenant (CC-13).

    ``cached`` marks a call served from the response cache (no provider spend).
    """

    __tablename__ = "llm_usage"

    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class LlmBudget(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A per-tenant LLM budget override. Null caps fall back to settings defaults."""

    __tablename__ = "llm_budget"
    __table_args__ = (UniqueConstraint("tenant_id"),)

    daily_token_cap: Mapped[int | None] = mapped_column(Integer)
    daily_call_cap: Mapped[int | None] = mapped_column(Integer)
