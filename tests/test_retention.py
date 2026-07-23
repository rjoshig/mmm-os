"""Tests for data retention + purge (Phase 10, Slice 1)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mmm_os.governance.retention import RetentionPolicy, run_retention
from mmm_os.models import File, LlmUsage, OutputRow, Sheet, Tenant
from mmm_os.models.mixins import utcnow
from mmm_os.storage.local import LocalObjectStorage


def test_expired_raw_file_purge_cascades(engine: Engine, storage: LocalObjectStorage) -> None:
    """An expired raw file is purged with its derived data + storage bytes; fresh stays."""
    key_old = "t/old/data.csv"
    key_new = "t/new/data.csv"
    from io import BytesIO

    storage.put(key_old, BytesIO(b"a,b\n1,2\n"))
    storage.put(key_new, BytesIO(b"a,b\n1,2\n"))

    with Session(engine) as session:
        tenant = Tenant(name="Acme", slug="acme")
        session.add(tenant)
        session.flush()
        now = utcnow()

        old_file = File(
            id=uuid.uuid4(), tenant_id=tenant.id, filename="data.csv", byte_size=8,
            storage_uri="x", created_at=now - timedelta(days=400),
        )
        new_file = File(
            id=uuid.uuid4(), tenant_id=tenant.id, filename="data.csv", byte_size=8,
            storage_uri="x", created_at=now,
        )
        session.add_all([old_file, new_file])
        session.flush()
        # storage_key_for derives key from tenant/id/filename — align the stored keys.
        from mmm_os.ingestion.service import storage_key_for

        storage.put(storage_key_for(old_file), BytesIO(b"a,b\n1,2\n"))
        session.add(Sheet(tenant_id=tenant.id, file_id=old_file.id, sheet_index=0, columns=[]))
        session.add(
            OutputRow(tenant_id=tenant.id, source_file_id=old_file.id, data={"x": 1})
        )
        session.flush()

        purged = run_retention(
            session, storage, now=now, policy=RetentionPolicy(raw_file_days=365)
        )
        assert purged["raw_file"] == 1

        remaining = session.scalars(select(File).where(File.tenant_id == tenant.id)).all()
        assert [f.id for f in remaining] == [new_file.id]  # only the fresh file remains
        # Derived data for the old file is gone.
        assert session.scalars(select(Sheet).where(Sheet.file_id == old_file.id)).all() == []
        assert (
            session.scalars(
                select(OutputRow).where(OutputRow.source_file_id == old_file.id)
            ).all()
            == []
        )
        assert not storage.exists(storage_key_for(old_file))


def test_standalone_class_purge_respects_window(
    engine: Engine, storage: LocalObjectStorage
) -> None:
    """LLM usage older than the window is purged; recent rows survive; 0 disables purge."""
    with Session(engine) as session:
        tenant = Tenant(name="Acme", slug="acme2")
        session.add(tenant)
        session.flush()
        now = utcnow()
        session.add(
            LlmUsage(
                tenant_id=tenant.id,
                model="m",
                prompt_tokens=5,
                completion_tokens=5,
                created_at=now - timedelta(days=200),
            )
        )
        session.add(
            LlmUsage(tenant_id=tenant.id, model="m", prompt_tokens=5, completion_tokens=5)
        )
        session.flush()

        purged = run_retention(
            session,
            storage,
            now=now,
            policy=RetentionPolicy(raw_file_days=0, llm_usage_days=90),
        )
        assert purged["llm_usage"] == 1
        assert len(session.scalars(select(LlmUsage)).all()) == 1


def test_retention_run_endpoint(client: TestClient) -> None:
    """The admin retention endpoint runs and returns a per-class summary."""
    tenant_id = uuid.uuid4()
    resp = client.post(f"/api/v1/tenants/{tenant_id}/retention/run")
    assert resp.status_code == 200, resp.text
    assert set(resp.json()["purged"]) >= {"raw_file", "llm_usage", "sync_run", "notification"}

    policy = client.get(f"/api/v1/tenants/{tenant_id}/retention/policy")
    assert policy.status_code == 200
    assert policy.json()["raw_file_days"] == 365
