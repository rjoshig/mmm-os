"""Tests for right-to-erasure (Phase 10, Slice 2)."""

from __future__ import annotations

import uuid
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from mmm_os.governance.erasure import erase_tenant
from mmm_os.ingestion.service import storage_key_for
from mmm_os.models import AuditLog, File, OutputRow, Sheet, Tenant, User
from mmm_os.storage.local import LocalObjectStorage


def _seed(session: Session, storage: LocalObjectStorage) -> uuid.UUID:
    tenant = Tenant(name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}")
    session.add(tenant)
    session.flush()
    session.add(User(tenant_id=tenant.id, email="u@acme.test", role="member"))
    session.add(AuditLog(tenant_id=tenant.id, action="something.happened"))
    file = File(
        id=uuid.uuid4(), tenant_id=tenant.id, filename="d.csv", byte_size=8, storage_uri="x"
    )
    session.add(file)
    session.flush()
    storage.put(storage_key_for(file), BytesIO(b"a,b\n1,2\n"))
    session.add(Sheet(tenant_id=tenant.id, file_id=file.id, sheet_index=0, columns=[]))
    session.add(OutputRow(tenant_id=tenant.id, source_file_id=file.id, data={"x": 1}))
    session.commit()
    return tenant.id


def test_erase_file_endpoint_removes_derived_and_bytes(
    client: TestClient, engine: Engine, storage: LocalObjectStorage
) -> None:
    """Erasing a file removes it, its derived rows, and its storage bytes."""
    with Session(engine) as session:
        tenant_id = _seed(session, storage)
        file = session.scalar(select(File).where(File.tenant_id == tenant_id))
        assert file is not None
        file_id = file.id
        key = storage_key_for(file)

    resp = client.post(f"/api/v1/tenants/{tenant_id}/erase/files/{file_id}")
    assert resp.status_code == 200, resp.text

    with Session(engine) as session:
        assert session.scalars(select(File).where(File.id == file_id)).all() == []
        assert session.scalars(select(Sheet).where(Sheet.file_id == file_id)).all() == []
    assert not storage.exists(key)


def test_erase_tenant_keeps_identity_and_audit(
    engine: Engine, storage: LocalObjectStorage
) -> None:
    """Full-tenant erasure wipes data but keeps user identity + the audit trail."""
    with Session(engine) as session:
        tenant_id = _seed(session, storage)

        erased = erase_tenant(session, storage, tenant_id)
        session.commit()
        assert erased.get("file") == 1 and erased.get("sheet") == 1

        # Data is gone…
        assert session.scalar(select(func.count()).select_from(File)) == 0
        assert session.scalar(select(func.count()).select_from(OutputRow)) == 0
        # …but identity + audit trail + tenant shell remain.
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(AuditLog)) == 1
        assert session.scalar(select(func.count()).select_from(Tenant)) == 1


def test_erase_tenant_requires_confirmation(client: TestClient) -> None:
    """The full-tenant erase endpoint refuses without the confirmation token."""
    tenant_id = uuid.uuid4()
    bad = client.post(f"/api/v1/tenants/{tenant_id}/erase", json={"confirm": "nope"})
    assert bad.status_code == 400
    ok = client.post(f"/api/v1/tenants/{tenant_id}/erase", json={"confirm": "ERASE"})
    assert ok.status_code == 200, ok.text
