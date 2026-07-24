"""Tenant KPI dashboard aggregates + active-run monitoring (Phase 20).

Read-only rollups over existing job/flag/stack/sync data (CC-1 tenant-scoped).
Sandbox jobs (Phase 18) are excluded from operational counts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import File, Job, Stack, SyncRun, ValidationFlag
from mmm_os.models.enums import JobStatus


@dataclass
class DashboardKPIs:
    """Tenant-level operational KPIs for the dashboard."""

    files_total: int = 0
    jobs_by_status: dict[str, int] = field(default_factory=dict)
    active_jobs: int = 0
    stacks_total: int = 0
    stacks_published: int = 0
    open_flags_by_severity: dict[str, int] = field(default_factory=dict)
    sync_by_status: dict[str, int] = field(default_factory=dict)


_ACTIVE_JOB_STATES = {JobStatus.PENDING.value, JobStatus.RUNNING.value}
_OPEN_FLAG_STATES = ("open", "acknowledged")


def dashboard_kpis(session: Session, tenant_id: uuid.UUID) -> DashboardKPIs:
    """Compute the tenant's dashboard KPIs (excludes sandbox jobs)."""
    files_total = (
        session.scalar(
            select(func.count()).select_from(File).where(File.tenant_id == tenant_id)
        )
        or 0
    )

    job_rows = session.execute(
        select(Job.status, func.count())
        .where(Job.tenant_id == tenant_id, Job.sandbox.is_(False))
        .group_by(Job.status)
    ).all()
    jobs_by_status = {str(s): int(c) for s, c in job_rows}
    active_jobs = sum(c for s, c in jobs_by_status.items() if s in _ACTIVE_JOB_STATES)

    stacks_total = (
        session.scalar(
            select(func.count()).select_from(Stack).where(Stack.tenant_id == tenant_id)
        )
        or 0
    )
    stacks_published = (
        session.scalar(
            select(func.count()).select_from(Stack).where(
                Stack.tenant_id == tenant_id, Stack.lifecycle_status == "published"
            )
        )
        or 0
    )

    flag_rows = session.execute(
        select(ValidationFlag.severity, func.count())
        .where(
            ValidationFlag.tenant_id == tenant_id,
            ValidationFlag.review_status.in_(_OPEN_FLAG_STATES),
        )
        .group_by(ValidationFlag.severity)
    ).all()
    open_flags_by_severity = {str(s): int(c) for s, c in flag_rows}

    sync_rows = session.execute(
        select(SyncRun.status, func.count())
        .where(SyncRun.tenant_id == tenant_id)
        .group_by(SyncRun.status)
    ).all()
    sync_by_status = {str(s): int(c) for s, c in sync_rows}

    return DashboardKPIs(
        files_total=int(files_total),
        jobs_by_status=jobs_by_status,
        active_jobs=active_jobs,
        stacks_total=int(stacks_total),
        stacks_published=int(stacks_published),
        open_flags_by_severity=open_flags_by_severity,
        sync_by_status=sync_by_status,
    )


def active_jobs(session: Session, tenant_id: uuid.UUID) -> list[Job]:
    """Return in-flight (pending/running) non-sandbox jobs for live monitoring."""
    return list(
        session.scalars(
            tenant_scoped_select(Job, tenant_id)
            .where(Job.status.in_(_ACTIVE_JOB_STATES), Job.sandbox.is_(False))
            .order_by(Job.created_at.desc())
        ).all()
    )
