"""Tenant dashboard + live-monitoring routes (Phase 20)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mmm_os.db.session import get_session
from mmm_os.schemas.dashboard import (
    ActiveJobRead,
    ActiveJobsResponse,
    DashboardResponse,
)
from mmm_os.services.dashboard import active_jobs, dashboard_kpis

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/tenants/{tenant_id}/dashboard", response_model=DashboardResponse)
def dashboard_route(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> DashboardResponse:
    """Return tenant KPIs: files, jobs by status, stacks, open flags, sync health."""
    kpis = dashboard_kpis(session, tenant_id)
    return DashboardResponse(**vars(kpis))


@router.get("/tenants/{tenant_id}/active-jobs", response_model=ActiveJobsResponse)
def active_jobs_route(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ActiveJobsResponse:
    """Return in-flight jobs for the live runs view to poll (Phase 20)."""
    jobs = active_jobs(session, tenant_id)
    return ActiveJobsResponse(
        active=[ActiveJobRead.model_validate(j, from_attributes=True) for j in jobs]
    )
