"""Tests for the in-app connector scheduler (Cycle 3, Slice 3)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.connectors.autoschedule import (
    is_due,
    next_run_at,
    run_due_syncs,
    schedule_interval_minutes,
)
from mmm_os.models import ConnectorConfig, Tenant
from mmm_os.models.mixins import utcnow


def _tenant_and_config(session: Session, *, schedule: dict | None) -> ConnectorConfig:
    tenant = Tenant(name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}")
    session.add(tenant)
    session.flush()
    settings: dict = {}
    if schedule is not None:
        settings["schedule"] = schedule
    config = ConnectorConfig(
        tenant_id=tenant.id,
        connector_key="meta",
        name="Meta",
        account_ids=["act_1"],
        settings=settings,
    )
    session.add(config)
    session.flush()
    return config


def test_schedule_interval_parsing() -> None:
    """interval_minutes is parsed; junk / missing / non-positive → unscheduled."""
    assert schedule_interval_minutes(_cfg({"interval_minutes": 60})) == 60
    assert schedule_interval_minutes(_cfg({"interval_minutes": 0})) is None
    assert schedule_interval_minutes(_cfg({"interval_minutes": "x"})) is None
    assert schedule_interval_minutes(_cfg(None)) is None


def _cfg(schedule: dict | None) -> ConnectorConfig:
    settings: dict = {} if schedule is None else {"schedule": schedule}
    return ConnectorConfig(
        tenant_id=uuid.uuid4(), connector_key="meta", name="Meta", account_ids=[], settings=settings
    )


def test_unscheduled_config_is_never_due(engine: Engine) -> None:
    """A config with no schedule is never due and has no next run."""
    with Session(engine) as session:
        config = _tenant_and_config(session, schedule=None)
        now = utcnow()
        assert next_run_at(config, session, now) is None
        assert is_due(config, session, now) is False


def test_newly_scheduled_config_is_due_immediately(engine: Engine) -> None:
    """A scheduled config that never ran is due right away."""
    with Session(engine) as session:
        config = _tenant_and_config(session, schedule={"interval_minutes": 60})
        now = utcnow()
        assert next_run_at(config, session, now) == now
        assert is_due(config, session, now) is True


def test_run_due_syncs_fires_and_then_waits(engine: Engine) -> None:
    """run_due_syncs runs a due config once, then it is not due until the interval passes."""
    with Session(engine) as session:
        config = _tenant_and_config(session, schedule={"interval_minutes": 60})
        tenant_id = config.tenant_id
        now = utcnow()

        first = run_due_syncs(session, now, tenant_id=tenant_id)
        assert len(first) == 1
        assert first[0].sync_run.status == "succeeded"

        # Immediately after, not due again (last run just finished).
        session.refresh(config)
        assert is_due(config, session, utcnow()) is False

        # After the interval elapses, it is due again.
        later = now + timedelta(minutes=61)
        assert is_due(config, session, later) is True


def test_scheduler_endpoints_set_and_run(client: TestClient) -> None:
    """PUT schedule stores the interval; run-due fires the due sync (manual trigger)."""
    tenant_id = uuid.uuid4()
    created = client.post(
        f"/api/v1/tenants/{tenant_id}/connector-configs",
        json={"connector_key": "meta", "name": "Meta", "account_ids": ["act_1"]},
    )
    config_id = created.json()["id"]

    scheduled = client.put(
        f"/api/v1/tenants/{tenant_id}/connector-configs/{config_id}/schedule",
        json={"interval_minutes": 30},
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["settings"]["schedule"]["interval_minutes"] == 30

    ran = client.post(f"/api/v1/tenants/{tenant_id}/scheduler/run-due")
    assert ran.status_code == 200, ran.text
    assert len(ran.json()["ran"]) == 1

    # No longer due immediately → a second run-due fires nothing.
    again = client.post(f"/api/v1/tenants/{tenant_id}/scheduler/run-due")
    assert again.json()["ran"] == []
