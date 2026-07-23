"""Per-tenant LLM budget accounting + enforcement (Phase 05.1, CC-13)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mmm_os.core.config import Settings
from mmm_os.models import LlmBudget, LlmUsage
from mmm_os.models.mixins import utcnow


@dataclass(frozen=True)
class UsageSnapshot:
    """Today's usage vs the effective caps for a tenant."""

    calls: int
    tokens: int
    token_cap: int  # 0 = unlimited
    call_cap: int  # 0 = unlimited

    @property
    def over_budget(self) -> bool:
        """Return whether either cap is set and already met/exceeded."""
        return (self.call_cap > 0 and self.calls >= self.call_cap) or (
            self.token_cap > 0 and self.tokens >= self.token_cap
        )


def _caps(session: Session, tenant_id: uuid.UUID, settings: Settings) -> tuple[int, int]:
    """Return ``(token_cap, call_cap)`` — a tenant override or the settings default."""
    budget = session.scalar(select(LlmBudget).where(LlmBudget.tenant_id == tenant_id))
    token_cap = settings.llm_tenant_daily_token_cap
    call_cap = settings.llm_tenant_daily_call_cap
    if budget is not None:
        if budget.daily_token_cap is not None:
            token_cap = budget.daily_token_cap
        if budget.daily_call_cap is not None:
            call_cap = budget.daily_call_cap
    return token_cap, call_cap


def usage_snapshot(session: Session, tenant_id: uuid.UUID, settings: Settings) -> UsageSnapshot:
    """Summarise a tenant's LLM usage over the last 24h against its caps."""
    since = utcnow() - timedelta(hours=24)
    row = session.execute(
        select(
            func.count(LlmUsage.id),
            func.coalesce(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens), 0),
        ).where(LlmUsage.tenant_id == tenant_id, LlmUsage.created_at >= since)
    ).one()
    token_cap, call_cap = _caps(session, tenant_id, settings)
    return UsageSnapshot(
        calls=int(row[0]), tokens=int(row[1]), token_cap=token_cap, call_cap=call_cap
    )
