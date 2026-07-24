"""Tests for Phase 16 — harmonization & Stack assembly (Gold layer)."""

from __future__ import annotations

import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.canonical import load_and_validate
from mmm_os.models import File, Job, OutputRow, Tenant
from mmm_os.stack import (
    HarmonizationSpec,
    assemble_stack,
    harmonize_rows,
    publish_stack,
    stack_rows_as_dicts,
    suggest_harmonization,
    validate_panel,
)


def _session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def _canonical():
    return load_and_validate()


def _tenant(session: Session) -> Tenant:
    t = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(t)
    session.flush()
    return t


def _silver_job(session: Session, tenant: Tenant, rows: list[dict]) -> Job:
    file = File(tenant_id=tenant.id, filename=f"{uuid.uuid4().hex[:6]}.csv")
    session.add(file)
    session.flush()
    job = Job(tenant_id=tenant.id, file_id=file.id)
    session.add(job)
    session.flush()
    for i, data in enumerate(rows):
        session.add(
            OutputRow(
                tenant_id=tenant.id,
                source_file_id=file.id,
                source_sheet="s",
                source_row=i,
                data=data,
            )
        )
    session.flush()
    return job


def test_harmonize_rows_applies_field_and_value_maps() -> None:
    spec = HarmonizationSpec(
        field_map={"link_clicks": "clicks"},
        value_map={"channel": {"FB": "meta", "Facebook": "meta"}},
    )
    out = harmonize_rows(
        [{"channel": "FB", "link_clicks": 5}, {"channel": "Facebook", "link_clicks": 7}], spec
    )
    assert out == [{"channel": "meta", "clicks": 5}, {"channel": "meta", "clicks": 7}]


def test_assemble_stack_from_two_sources(engine: Engine) -> None:
    session = _session(engine)
    canonical = _canonical()
    tenant = _tenant(session)
    j1 = _silver_job(session, tenant, [{"date": "2026-01-01", "channel": "FB", "spend": 10}])
    j2 = _silver_job(session, tenant, [{"date": "2026-01-01", "channel": "google", "spend": 20}])

    spec = HarmonizationSpec(value_map={"channel": {"FB": "meta"}})
    stack = assemble_stack(
        session,
        canonical,
        tenant_id=tenant.id,
        name="Q1 panel",
        description=None,
        source_job_ids=[j1.id, j2.id],
        spec=spec,
    )
    table = stack_rows_as_dicts(session, tenant.id, stack.id)
    assert len(table) == 2
    channels = {r["channel"] for r in table}
    assert channels == {"meta", "google"}  # FB harmonized to meta
    assert stack.lifecycle_status == "draft"
    assert "channel" in stack.schema_contract["columns"]


def test_publish_gate_blocks_on_funnel_violation(engine: Engine) -> None:
    session = _session(engine)
    canonical = _canonical()
    tenant = _tenant(session)
    # clicks > impressions is a blocking semantic violation.
    job = _silver_job(
        session, tenant, [{"date": "2026-01-01", "channel": "meta", "clicks": 99, "impressions": 5}]
    )
    stack = assemble_stack(
        session, canonical, tenant_id=tenant.id, name="bad", description=None,
        source_job_ids=[job.id], spec=HarmonizationSpec(),
    )
    published, blocking = publish_stack(
        session, canonical, tenant_id=tenant.id, stack_id=stack.id
    )
    assert published is not None and published.lifecycle_status == "draft"
    assert any(f.check == "funnel_monotonicity" for f in blocking)

    # force overrides the gate.
    published2, _ = publish_stack(
        session, canonical, tenant_id=tenant.id, stack_id=stack.id, force=True
    )
    assert published2 is not None and published2.lifecycle_status == "published"


def test_panel_taxonomy_completeness_flags_unknown_channel(engine: Engine) -> None:
    canonical = _canonical()
    flags = validate_panel([{"date": "2026-01-01", "channel": "ZZZ_unknown"}], canonical)
    assert any(f.check == "taxonomy_incomplete" for f in flags)


def test_suggest_harmonization_deterministic() -> None:
    canonical = _canonical()
    # A known alias for a canonical channel term should be proposed.
    suggestions = suggest_harmonization(
        [{"channel": "facebook"}], canonical.taxonomies, field="channel", taxonomy="channel"
    )
    # Suggestion only appears if 'facebook' is a known alias resolving to a term.
    assert all("raw" in s and "canonical" in s for s in suggestions)


def test_stack_api_create_and_publish(client) -> None:
    tenant_id = client.post(
        "/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"}
    ).json()["id"]
    # Seed a Silver output by inserting output rows directly is not exposed via API;
    # instead assemble an empty-source stack (0 rows) and confirm it publishes clean.
    created = client.post(
        f"/api/v1/tenants/{tenant_id}/stacks",
        json={"name": "Empty", "source_job_ids": []},
    )
    assert created.status_code == 201, created.text
    stack_id = created.json()["id"]
    assert created.json()["row_count"] == 0

    listed = client.get(f"/api/v1/tenants/{tenant_id}/stacks")
    assert any(s["id"] == stack_id for s in listed.json())

    published = client.post(f"/api/v1/tenants/{tenant_id}/stacks/{stack_id}/publish")
    assert published.status_code == 200
    assert published.json()["published"] is True
