"""Tenant-isolation hardening tests (Phase 7, P7-4 / CC-1).

Verify there is no cross-tenant access path through the tenant-scoping helper or
the read endpoints — one tenant can never see another's data.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import File


def _upload(client: TestClient, tenant_id: uuid.UUID) -> str:
    resp = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("d.csv", b"a,b\n1,2\n", "text/csv")},
    )
    return str(resp.json()["file"]["id"])


def test_scoped_select_excludes_other_tenants(client: TestClient, engine: Engine) -> None:
    """tenant_scoped_select never returns another tenant's rows (CC-1)."""
    t1, t2 = uuid.uuid4(), uuid.uuid4()
    _upload(client, t1)
    _upload(client, t2)

    with Session(engine) as session:
        t1_files = session.scalars(tenant_scoped_select(File, t1)).all()
        t2_files = session.scalars(tenant_scoped_select(File, t2)).all()
        assert len(t1_files) == 1 and len(t2_files) == 1
        assert {f.tenant_id for f in t1_files} == {t1}
        assert {f.tenant_id for f in t2_files} == {t2}


def test_read_endpoints_are_tenant_scoped(client: TestClient) -> None:
    """A tenant's file is invisible (list) and 404 (detail) to another tenant."""
    t1, t2 = uuid.uuid4(), uuid.uuid4()
    file_id = _upload(client, t1)

    assert client.get(f"/api/v1/tenants/{t2}/files").json() == []
    assert client.get(f"/api/v1/tenants/{t2}/files/{file_id}").status_code == 404
    # The owning tenant still sees it.
    assert len(client.get(f"/api/v1/tenants/{t1}/files").json()) == 1
