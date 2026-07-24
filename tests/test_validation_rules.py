"""Tests for Part 3 — first-class custom validation rules + wiring."""

from __future__ import annotations

import uuid

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.canonical import load_and_validate
from mmm_os.models import OutputRow, Tenant
from mmm_os.services.validation_rule import active_validation_rules, create_rule
from mmm_os.validation.custom import ValidationRuleSpec, run_validation_rules
from mmm_os.validation.service import run_validation


def _session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def _tenant(session: Session) -> Tenant:
    t = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(t)
    session.flush()
    return t


def test_run_validation_rules_applies_per_rule_severity() -> None:
    rules = [ValidationRuleSpec("funnel", "clicks <= impressions", "blocking")]
    flags = run_validation_rules([{"clicks": 50, "impressions": 5}], rules)
    assert flags and flags[0].severity == "blocking"
    assert flags[0].check == "custom:funnel"
    # Passing data → no flag.
    assert run_validation_rules([{"clicks": 5, "impressions": 50}], rules) == []


def test_unsafe_expression_flags_not_executes() -> None:
    flags = run_validation_rules([{"x": 1}], [ValidationRuleSpec("evil", "__import__('os')")])
    assert flags and flags[0].location["check_name"] == "evil"


def test_active_rules_excludes_disabled(engine: Engine) -> None:
    session = _session(engine)
    tenant = _tenant(session)
    create_rule(session, tenant.id, name="on", expression="clicks <= impressions")
    create_rule(session, tenant.id, name="off", expression="spend >= 0", enabled=False)
    specs = active_validation_rules(session, tenant.id)
    names = {s.name for s in specs}
    assert "on" in names and "off" not in names


def test_run_validation_wires_tenant_rules_and_blocks(engine: Engine) -> None:
    session = _session(engine)
    schema = load_and_validate().schema
    tenant = _tenant(session)
    create_rule(
        session,
        tenant.id,
        name="funnel",
        expression="clicks <= impressions",
        severity="blocking",
    )
    job_id = uuid.uuid4()
    flags, blocked = run_validation(
        session,
        tenant_id=tenant.id,
        job_id=job_id,
        table=[{"date": "2026-01-01", "channel": "meta", "clicks": 99, "impressions": 5}],
        schema=schema,
        rules=active_validation_rules(session, tenant.id),
    )
    assert blocked is True
    custom = [f for f in flags if f.location.get("check") == "custom:funnel"]
    assert custom and custom[0].severity == "blocking"


def test_validation_rule_api_crud(client) -> None:
    tenant_id = client.post(
        "/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"}
    ).json()["id"]

    created = client.post(
        f"/api/v1/tenants/{tenant_id}/validation-rules",
        json={"name": "funnel", "expression": "clicks <= impressions", "severity": "blocking"},
    )
    assert created.status_code == 201, created.text
    rule_id = created.json()["id"]

    listed = client.get(f"/api/v1/tenants/{tenant_id}/validation-rules")
    assert any(r["id"] == rule_id for r in listed.json())

    # Toggle disabled.
    patched = client.patch(
        f"/api/v1/tenants/{tenant_id}/validation-rules/{rule_id}", json={"enabled": False}
    )
    assert patched.status_code == 200 and patched.json()["enabled"] is False

    # Invalid severity rejected.
    bad = client.post(
        f"/api/v1/tenants/{tenant_id}/validation-rules",
        json={"name": "x", "expression": "spend >= 0", "severity": "nuclear"},
    )
    assert bad.status_code == 422

    deleted = client.delete(f"/api/v1/tenants/{tenant_id}/validation-rules/{rule_id}")
    assert deleted.status_code == 204


def test_end_to_end_rule_blocks_pipeline_output(client, engine: Engine) -> None:
    """A blocking custom rule, added via API, blocks real pipeline output."""
    tenant_id = client.post(
        "/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"}
    ).json()["id"]
    client.post(
        f"/api/v1/tenants/{tenant_id}/validation-rules",
        json={"name": "funnel", "expression": "clicks <= impressions", "severity": "blocking"},
    )
    # Upload a CSV where clicks > impressions, process, and map the columns.
    up = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={
            "upload": (
                "x.csv",
                b"date,channel,clicks,impressions\n2026-01-01,meta,100,5\n",
                "text/csv",
            )
        },
    )
    file_id = up.json()["file"]["id"]
    processed = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    sheet_id = processed.json()["sheets"][0]["id"]
    client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/mapping",
        json={
            "name": "m",
            "mapping": {
                "date": "date",
                "channel": "channel",
                "clicks": "clicks",
                "impressions": "impressions",
            },
        },
    )
    run = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/run-pipeline")
    assert run.status_code in (200, 201), run.text
    # The blocking custom rule prevents output for the violating sheet.
    assert any(s["blocked"] for s in run.json()["sheets"])
    with Session(engine) as session:
        rows = session.scalars(
            select(OutputRow).where(OutputRow.tenant_id == uuid.UUID(tenant_id))
        ).all()
        assert rows == []
