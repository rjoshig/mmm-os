"""Tests for Phase 18 — in-app sandbox / test environment."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mmm_os.models import Job, OutputRow


def _upload_and_process(client: TestClient, tenant_id: uuid.UUID) -> str:
    resp = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("x.csv", b"date,channel,spend\n2026-01-01,Facebook,100\n", "text/csv")},
    )
    assert resp.status_code in (200, 201), resp.text
    file_id = resp.json()["file"]["id"]
    processed = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    assert processed.status_code in (200, 201), processed.text
    return processed.json()["sheets"][0]["id"]


def test_job_sandbox_defaults_false(engine: Engine) -> None:
    from mmm_os.models import Tenant

    with Session(engine) as session:
        t = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
        session.add(t)
        session.flush()
        job = Job(tenant_id=t.id)
        session.add(job)
        session.flush()
        assert job.sandbox is False


def test_sandbox_run_writes_no_output(client: TestClient, engine: Engine) -> None:
    tenant_id = uuid.uuid4()
    sheet_id = _upload_and_process(client, tenant_id)

    resp = client.post(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/sandbox-run")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_sandbox"] is True
    assert body["row_count"] >= 1

    # Crucially, no real output rows were written.
    with Session(engine) as session:
        rows = session.scalars(
            select(OutputRow).where(OutputRow.tenant_id == tenant_id)
        ).all()
        assert rows == []


def test_sandbox_run_missing_sheet_404(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    resp = client.post(f"/api/v1/tenants/{tenant_id}/sheets/{uuid.uuid4()}/sandbox-run")
    assert resp.status_code == 404
