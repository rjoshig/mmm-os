"""Automatic connector scheduling (Cycle 3): "define a source, it runs".

A connector config carries an optional schedule in ``settings.schedule`` (an
``interval_minutes``). :func:`run_due_syncs` finds enabled partner configs whose
next run is due (based on their last successful sync) and runs an incremental sync
for each — idempotently (CC-6). It is a pure function of ``(session, now)`` so it is
unit-testable; a background loop (gated by ``scheduler_enabled``) and a manual
endpoint both call it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from mmm_os.secrets import SecretStore

from mmm_os.connectors.registry import PARTNER_KEYS, build_partner_connector
from mmm_os.connectors.scheduling import (
    SyncResult,
    incremental_window,
    latest_successful_run,
    run_sync,
)
from mmm_os.models import ConnectorConfig


def schedule_interval_minutes(config: ConnectorConfig) -> int | None:
    """Return the config's scheduled interval in minutes, or ``None`` if unscheduled."""
    schedule = config.settings.get("schedule")
    if not isinstance(schedule, dict):
        return None
    minutes = schedule.get("interval_minutes")
    if minutes is None:
        return None
    try:
        value = int(minutes)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def next_run_at(config: ConnectorConfig, session: Session, now: datetime) -> datetime | None:
    """Return when the config is next due, or ``None`` if it has no schedule.

    A config that has never successfully run is due immediately (``now``); otherwise
    it is due ``interval_minutes`` after its last successful sync finished.
    """
    interval = schedule_interval_minutes(config)
    if interval is None:
        return None
    last = latest_successful_run(session, config.id)
    if last is None or last.finished_at is None:
        return now
    # SQLite returns naive datetimes; treat a naive DB timestamp as UTC so it can be
    # compared with the timezone-aware ``now``.
    finished = last.finished_at
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=timezone.utc)
    return finished + timedelta(minutes=interval)


def is_due(config: ConnectorConfig, session: Session, now: datetime) -> bool:
    """Whether an enabled, scheduled partner config should run at ``now``."""
    if not config.enabled or config.connector_key not in PARTNER_KEYS:
        return False
    scheduled = next_run_at(config, session, now)
    return scheduled is not None and scheduled <= now


def run_due_syncs(
    session: Session,
    now: datetime,
    *,
    tenant_id: uuid.UUID | None = None,
    exclude_tenant_ids: set[uuid.UUID] | None = None,
) -> list[SyncResult]:
    """Run an incremental sync for every due config (optionally within one tenant).

    Args:
        session: The database session.
        now: The current time (timezone-aware).
        tenant_id: If given, only that tenant's configs are considered.
        exclude_tenant_ids: Tenants to skip (e.g. silo customers handled on their
            own engine by :func:`run_all_due_syncs`).

    Returns:
        The sync results for the configs that ran (empty if none were due).
    """
    query = select(ConnectorConfig).where(ConnectorConfig.enabled.is_(True))
    if tenant_id is not None:
        query = query.where(ConnectorConfig.tenant_id == tenant_id)
    if exclude_tenant_ids:
        query = query.where(ConnectorConfig.tenant_id.not_in(exclude_tenant_ids))
    results: list[SyncResult] = []
    for config in session.scalars(query).all():
        if not is_due(config, session, now):
            continue
        connector = build_partner_connector(
            config.connector_key, account_ctx=config.settings.get("account_ctx", {})
        )
        results.append(run_sync(session, connector, config, incremental_window(config, now.date())))
    return results


def run_all_due_syncs(
    control_session: Session, store: SecretStore, now: datetime
) -> list[SyncResult]:
    """Run due syncs across all customers, routing silo customers to their DB (7.6).

    The background scheduler runs outside any request, so it cannot rely on the
    per-request engine routing. This drives it explicitly: pool-tier customers are
    handled in one pass on the shared (control) session, and **each silo customer
    runs on its own engine** so its ``SyncRun`` rows land in its database, never the
    pool. Silo customers are excluded from the pool pass to prevent a stale pool-side
    config from running there.

    Args:
        control_session: A session bound to the pool (control-plane) database.
        store: The secret store holding dedicated DB URLs.
        now: The current time (timezone-aware).

    Returns:
        The combined sync results across the pool and every silo customer.
    """
    from sqlalchemy.orm import Session as _Session

    from mmm_os.db import routing
    from mmm_os.models import Tenant

    silo_tenants = list(
        control_session.scalars(select(Tenant).where(Tenant.isolation_mode == "silo")).all()
    )
    silo_ids = {t.id for t in silo_tenants}

    results = run_due_syncs(control_session, now, exclude_tenant_ids=silo_ids)
    control_session.commit()

    for tenant in silo_tenants:
        url = routing.get_dedicated_database_url(store, tenant.id)
        if not url:
            continue
        with _Session(routing.get_engine(url)) as silo:
            results.extend(run_due_syncs(silo, now, tenant_id=tenant.id))
            silo.commit()
    return results
