"""Tests for Phase 14 — config-driven I/O paths & destinations (CC-14)."""

from __future__ import annotations

import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.core.config import get_settings
from mmm_os.models import File, Job, JobEvent, OutputRow, Tenant
from mmm_os.output import record_file_lifecycle, render_output_csv, write_output_to_destination
from mmm_os.services.io_profile import resolve_io_profile, update_io_profile
from mmm_os.storage.local import LocalObjectStorage


def _canonical():
    from mmm_os.canonical import load_and_validate

    return load_and_validate()


def _session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def test_resolve_falls_back_to_env_defaults(engine: Engine) -> None:
    session = _session(engine)
    tenant = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    session.flush()

    resolved = resolve_io_profile(session, tenant.id, get_settings())
    assert resolved.output == "output"
    assert resolved.archive == "archive"
    assert resolved.reject == "reject"


def test_tenant_override_beats_global_and_env(engine: Engine) -> None:
    session = _session(engine)
    tenant = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    session.flush()

    # Global default sets output; tenant overrides it.
    update_io_profile(session, None, output_path="global-out", archive_path="global-arch")
    update_io_profile(session, tenant.id, output_path="tenant-out")

    resolved = resolve_io_profile(session, tenant.id, get_settings())
    assert resolved.output == "tenant-out"  # tenant wins
    assert resolved.archive == "global-arch"  # falls back to global
    assert resolved.reject == "reject"  # falls back to env default


def test_write_output_to_destination_writes_csv(engine: Engine, tmp_path) -> None:
    session = _session(engine)
    storage = LocalObjectStorage(tmp_path / "storage")
    canonical = _canonical()

    tenant = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    session.flush()
    file = File(tenant_id=tenant.id, filename="data.csv")
    session.add(file)
    session.flush()
    job = Job(tenant_id=tenant.id, file_id=file.id)
    session.add(job)
    session.flush()
    session.add(
        OutputRow(
            tenant_id=tenant.id,
            source_file_id=file.id,
            source_sheet="Sheet1",
            source_row=0,
            data={"date": "2026-01-01", "channel": "meta", "spend": 100},
        )
    )
    session.flush()

    key = write_output_to_destination(
        session, storage, canonical, tenant_id=tenant.id, job_id=job.id
    )
    assert key is not None and key.startswith("output/")
    assert storage.exists(key)
    body = storage.open(key).read().decode()
    assert "channel" in body and "meta" in body

    # A JobEvent records the destination write (CC-7).
    events = session.query(JobEvent).filter(JobEvent.job_id == job.id).all()
    assert any(e.stage == "output.destination" for e in events)

    # Re-writing overwrites the derived artifact (idempotent).
    key2 = write_output_to_destination(
        session, storage, canonical, tenant_id=tenant.id, job_id=job.id
    )
    assert key2 == key


def test_render_output_csv_orders_canonical_columns(engine: Engine) -> None:
    canonical = _canonical()
    rows = [
        OutputRow(
            tenant_id=uuid.uuid4(),
            source_sheet="s",
            source_row=0,
            data={"channel": "meta", "date": "2026-01-01", "spend": 5},
        )
    ]
    csv_bytes = render_output_csv(canonical, rows)
    header = csv_bytes.decode().splitlines()[0]
    # date (dimension) precedes spend (measure) in schema order.
    assert header.index("date") < header.index("spend")
    assert "source_sheet" in header


def test_record_file_lifecycle_emits_event(engine: Engine) -> None:
    session = _session(engine)
    tenant = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    session.flush()
    file = File(tenant_id=tenant.id, filename="data.csv")
    session.add(file)
    session.flush()
    job = Job(tenant_id=tenant.id, file_id=file.id)
    session.add(job)
    session.flush()

    key = record_file_lifecycle(
        session, tenant_id=tenant.id, job_id=job.id, file_id=file.id, outcome="error"
    )
    assert key.startswith("error/")
    events = session.query(JobEvent).filter(JobEvent.job_id == job.id).all()
    assert any(e.stage == "file.lifecycle" and e.status == "error" for e in events)


def test_io_profile_api_roundtrip(client) -> None:
    tenant_id = _create_tenant(client)
    # default resolves to env defaults
    got = client.get(f"/api/v1/tenants/{tenant_id}/io-profile")
    assert got.status_code == 200
    assert got.json()["output"] == "output"
    # update
    put = client.put(
        f"/api/v1/tenants/{tenant_id}/io-profile",
        json={"output_path": "exports/mmm"},
    )
    assert put.status_code == 200
    assert put.json()["output"] == "exports/mmm"


def _create_tenant(client) -> str:
    resp = client.post("/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]
