"""Tests for Phase 21 — tenant-scoped extensibility (ADR-015, CC-1/CC-4)."""

from __future__ import annotations

import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.canonical import load_and_validate
from mmm_os.models import OutputRow, Tenant
from mmm_os.services.schema_extension import (
    custom_checks,
    register_extension,
    resolved_fields,
)
from mmm_os.validation.custom import run_custom_checks


def _session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def _tenant(session: Session) -> Tenant:
    t = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(t)
    session.flush()
    return t


def test_custom_dimension_appears_in_resolved_schema(engine: Engine) -> None:
    session = _session(engine)
    canonical = load_and_validate()
    tenant = _tenant(session)

    register_extension(session, tenant.id, kind="dimension", name="brand", data_type="string")
    fields = resolved_fields(session, tenant.id, canonical)

    core = [f for f in fields if f.source == "core"]
    ext = [f for f in fields if f.source == "extension"]
    assert any(f.name == "date" for f in core)  # core still present
    assert any(f.name == "brand" and f.kind == "dimension" for f in ext)


def test_extension_values_persist_in_json_without_migration(engine: Engine) -> None:
    session = _session(engine)
    tenant = _tenant(session)
    register_extension(session, tenant.id, kind="dimension", name="brand")

    # A custom field is just an extra JSON key — no schema migration needed.
    row = OutputRow(
        tenant_id=tenant.id,
        source_sheet="s",
        source_row=0,
        data={"date": "2026-01-01", "channel": "meta", "brand": "acme"},
    )
    session.add(row)
    session.flush()
    fetched = session.get(OutputRow, row.id)
    assert fetched is not None and fetched.data["brand"] == "acme"


def test_extension_is_tenant_isolated(engine: Engine) -> None:
    session = _session(engine)
    canonical = load_and_validate()
    a, b = _tenant(session), _tenant(session)
    register_extension(session, a.id, kind="measure", name="video_views", data_type="number")

    a_fields = {f.name for f in resolved_fields(session, a.id, canonical)}
    b_fields = {f.name for f in resolved_fields(session, b.id, canonical)}
    assert "video_views" in a_fields
    assert "video_views" not in b_fields  # CC-1


def test_custom_check_fires_via_sandbox(engine: Engine) -> None:
    session = _session(engine)
    tenant = _tenant(session)
    register_extension(
        session,
        tenant.id,
        kind="measure",
        name="ok_flag",
        validation="clicks <= impressions",
    )
    checks = custom_checks(session, tenant.id)
    assert checks == [("ok_flag", "clicks <= impressions")]

    findings = run_custom_checks([{"clicks": 50, "impressions": 5}], checks)
    assert any(f.check == "custom_check" for f in findings)
    # Passing data yields no finding.
    assert run_custom_checks([{"clicks": 5, "impressions": 50}], checks) == []


def test_custom_check_rejects_unsafe_expression(engine: Engine) -> None:
    # An expression using a disallowed construct flags rather than executing.
    findings = run_custom_checks([{"x": 1}], [("evil", "__import__('os')")])
    assert findings and findings[0].location["check_name"] == "evil"


def test_schema_extension_api_roundtrip(client) -> None:
    resp = client.post("/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"})
    tenant_id = resp.json()["id"]

    created = client.post(
        f"/api/v1/tenants/{tenant_id}/schema-extensions",
        json={"kind": "factor", "name": "weather_index", "data_type": "number"},
    )
    assert created.status_code == 201, created.text

    resolved = client.get(f"/api/v1/tenants/{tenant_id}/resolved-schema")
    names = {f["name"] for f in resolved.json()["fields"]}
    assert "weather_index" in names and "date" in names

    bad = client.post(
        f"/api/v1/tenants/{tenant_id}/schema-extensions",
        json={"kind": "widget", "name": "x"},
    )
    assert bad.status_code == 422
