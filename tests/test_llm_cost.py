"""Tests for Phase-05.1 LLM cost controls (metering, cache, budget, routing)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from mmm_os.ai import cache
from mmm_os.ai.config import LLMConfig, route_model
from mmm_os.ai.errors import LLMBudgetExceededError
from mmm_os.ai.metering import MeteringLLMClient
from mmm_os.core.config import Settings
from mmm_os.models import LlmUsage


class _FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *, system: str, user: str) -> str:
        self.calls += 1
        return f"reply-{self.calls}"


def _metered(session: Session, tenant_id: uuid.UUID, settings: Settings) -> tuple:
    inner = _FakeClient()
    client = MeteringLLMClient(
        inner, session=session, tenant_id=tenant_id, model="gpt-test", settings=settings
    )
    return inner, client


def test_usage_is_recorded(engine: Engine) -> None:
    """Each completion records an llm_usage row for the tenant."""
    cache.clear()
    tid = uuid.uuid4()
    with Session(engine) as session:
        _, client = _metered(session, tid, Settings(llm_cache_enabled=False))
        client.complete(system="s", user="u")
        session.commit()
        n = session.scalar(select(func.count(LlmUsage.id)).where(LlmUsage.tenant_id == tid))
        assert n == 1


def test_cache_hit_skips_provider(engine: Engine) -> None:
    """An identical prompt is served from cache (no second provider call)."""
    cache.clear()
    tid = uuid.uuid4()
    with Session(engine) as session:
        inner, client = _metered(session, tid, Settings(llm_cache_enabled=True))
        first = client.complete(system="s", user="u")
        second = client.complete(system="s", user="u")
        assert first == second
        assert inner.calls == 1  # second served from cache
        cached_rows = session.scalars(
            select(LlmUsage).where(LlmUsage.tenant_id == tid, LlmUsage.cached.is_(True))
        ).all()
        assert len(cached_rows) == 1


def test_budget_cap_blocks(engine: Engine) -> None:
    """Once the daily call cap is reached, further calls raise (→ 429)."""
    cache.clear()
    tid = uuid.uuid4()
    settings = Settings(llm_cache_enabled=False, llm_tenant_daily_call_cap=1)
    with Session(engine) as session:
        _, client = _metered(session, tid, settings)
        client.complete(system="s", user="u1")
        session.commit()
        with pytest.raises(LLMBudgetExceededError):
            client.complete(system="s", user="u2")


def test_route_model_prefers_cheap() -> None:
    """Tier routing uses the cheap model by default, strong when needed."""
    cfg = LLMConfig(model="m", model_cheap="cheap", model_strong="strong")
    assert route_model(cfg) == "cheap"
    assert route_model(cfg, needs_strong=True) == "strong"


def test_usage_endpoint(client: TestClient) -> None:
    """The usage endpoint returns a snapshot (zeros for a fresh tenant)."""
    tid = uuid.uuid4()
    resp = client.get(f"/api/v1/tenants/{tid}/llm-usage")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["calls"] == 0 and body["tokens"] == 0 and body["over_budget"] is False
