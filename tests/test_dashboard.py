"""Tests for Phase 20 — tenant dashboard + live monitoring."""

from __future__ import annotations

import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.models import File, Job, Stack, Tenant, ValidationFlag
from mmm_os.models.enums import JobStatus, Severity
from mmm_os.services.dashboard import active_jobs, dashboard_kpis


def _session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def test_dashboard_kpis_aggregate(engine: Engine) -> None:
    session = _session(engine)
    tenant = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    session.flush()
    file = File(tenant_id=tenant.id, filename="a.csv")
    session.add(file)
    session.flush()
    # a running (active) job, a succeeded job, and a sandbox job (excluded)
    session.add(Job(tenant_id=tenant.id, file_id=file.id, status=JobStatus.RUNNING.value))
    succeeded = Job(tenant_id=tenant.id, file_id=file.id, status=JobStatus.SUCCEEDED.value)
    session.add(succeeded)
    session.add(Job(tenant_id=tenant.id, status=JobStatus.RUNNING.value, sandbox=True))
    session.flush()  # assign job ids before referencing them
    # a published + a draft stack
    session.add(Stack(tenant_id=tenant.id, name="s1", lifecycle_status="published"))
    session.add(Stack(tenant_id=tenant.id, name="s2", lifecycle_status="draft"))
    # an open blocking flag
    session.add(
        ValidationFlag(
            tenant_id=tenant.id, job_id=succeeded.id, severity=Severity.BLOCKING.value,
            description="x", review_status="open",
        )
    )
    session.flush()

    kpis = dashboard_kpis(session, tenant.id)
    assert kpis.files_total == 1
    assert kpis.active_jobs == 1  # sandbox running job excluded
    assert kpis.jobs_by_status.get("running") == 1  # sandbox excluded from counts
    assert kpis.stacks_total == 2 and kpis.stacks_published == 1
    assert kpis.open_flags_by_severity.get("blocking") == 1

    active = active_jobs(session, tenant.id)
    assert len(active) == 1  # the one non-sandbox running job


def test_dashboard_api(client) -> None:
    tenant_id = client.post(
        "/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"}
    ).json()["id"]
    resp = client.get(f"/api/v1/tenants/{tenant_id}/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["files_total"] == 0 and body["stacks_total"] == 0

    active = client.get(f"/api/v1/tenants/{tenant_id}/active-jobs")
    assert active.status_code == 200 and active.json()["active"] == []
