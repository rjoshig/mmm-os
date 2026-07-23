"""Sync orchestration: run a partner pull over a window (Phase 09.6).

Computes incremental (rolling-lookback) and backfill windows, runs a connector's
``fetch`` under a ``SyncRun`` record (status/row counts/errors, CC-7), and makes
re-pulls **idempotent** — re-running the same (config, window) replaces the prior
run rather than duplicating it (CC-6). Runs on the Phase-7 ``TaskQueue`` in
production; here it executes inline for a deterministic, testable flow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mmm_os.connectors.base import PartnerConnector
from mmm_os.models import ConnectorConfig, SyncRun
from mmm_os.models.enums import JobStatus
from mmm_os.models.mixins import utcnow
from mmm_os.observability import registry
from mmm_os.sources.base import FetchRequest
from mmm_os.sources.landed import LandedDataset


@dataclass
class SyncResult:
    """The outcome of a sync: the record + the landed dataset."""

    sync_run: SyncRun
    dataset: LandedDataset | None


def incremental_window(config: ConnectorConfig, today: date) -> tuple[date, date]:
    """Return a rolling-lookback window ending today (absorbs restatements)."""
    lookback = int(config.settings.get("lookback_days", 7))
    return today - timedelta(days=lookback), today


def backfill_window(config: ConnectorConfig, today: date) -> tuple[date, date]:
    """Return a historical backfill window ending today."""
    days = int(config.settings.get("backfill_days", 90))
    return today - timedelta(days=days), today


def run_sync(
    session: Session,
    connector: PartnerConnector,
    config: ConnectorConfig,
    window: tuple[date, date],
    *,
    created_by: uuid.UUID | None = None,
) -> SyncResult:
    """Run a connector pull for ``window`` under an idempotent ``SyncRun`` (CC-6)."""
    start, end = window
    # Idempotent re-pull: drop any prior run for this exact window before re-fetching.
    session.execute(
        delete(SyncRun).where(
            SyncRun.connector_config_id == config.id,
            SyncRun.window_start == start,
            SyncRun.window_end == end,
        )
    )
    run = SyncRun(
        tenant_id=config.tenant_id,
        connector_config_id=config.id,
        window_start=start,
        window_end=end,
        status=JobStatus.RUNNING.value,
        started_at=utcnow(),
        created_by=created_by,
    )
    session.add(run)
    session.flush()

    try:
        dataset = connector.fetch(
            FetchRequest(
                ref={"connector_config_id": str(config.id), "sync_run_id": str(run.id)},
                config=config.settings,
                date_range=window,
            )
        )
        run.row_count = sum(len(t.records or []) for t in dataset.tables)
        run.status = JobStatus.SUCCEEDED.value
        registry.increment("connector.rows", float(run.row_count), connector=config.connector_key)
    except Exception as exc:  # noqa: BLE001 - a failed sync is recorded, not raised
        dataset = None
        run.status = JobStatus.FAILED.value
        run.error = str(exc)
    run.finished_at = utcnow()
    session.flush()
    return SyncResult(sync_run=run, dataset=dataset)


def latest_successful_run(session: Session, config_id: uuid.UUID) -> SyncRun | None:
    """Return a config's most recent succeeded sync run, if any (observability)."""
    return session.scalar(
        select(SyncRun)
        .where(
            SyncRun.connector_config_id == config_id,
            SyncRun.status == JobStatus.SUCCEEDED.value,
        )
        .order_by(SyncRun.finished_at.desc())
    )
