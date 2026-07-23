"""Tests for output export + the Export-to-MMM contract (Cycle 3, Slice 4)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.models import File, Job, OutputRow, Tenant
from mmm_os.models.enums import JobStatus


def _seed_output(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a tenant + file + job + two weekly output rows; return (tenant_id, job_id)."""
    with Session(engine) as session:
        tenant = Tenant(name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        session.flush()
        file = File(tenant_id=tenant.id, filename="meta_us.xlsx", byte_size=10, storage_uri="x")
        session.add(file)
        session.flush()
        job = Job(tenant_id=tenant.id, file_id=file.id, status=JobStatus.SUCCEEDED.value)
        session.add(job)
        for i, (date, spend) in enumerate([("2026-01-05", 150.0), ("2026-01-12", 200.0)]):
            session.add(
                OutputRow(
                    tenant_id=tenant.id,
                    source_file_id=file.id,
                    source_sheet="sheet-1",
                    source_row=i,
                    mapping_config_version=1,
                    rule_set_version=2,
                    data={"date": date, "channel": "Facebook", "spend": spend, "price_index": 1.1},
                )
            )
        session.commit()
        return tenant.id, job.id


def test_output_contract_lists_columns_and_sample(client: TestClient, engine: Engine) -> None:
    """The contract reports canonical columns (with kind), row count, versions, sample."""
    tenant_id, job_id = _seed_output(engine)
    resp = client.get(f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/output/contract")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["row_count"] == 2
    assert body["mapping_config_version"] == 1
    assert body["rule_set_version"] == 2
    kinds = {c["name"]: c["kind"] for c in body["columns"]}
    assert kinds["date"] == "dimension"
    assert kinds["channel"] == "dimension"
    assert kinds["spend"] == "measure"
    assert kinds["price_index"] == "factor"  # factors surface in the MMM contract
    assert len(body["sample"]) == 2


def test_output_csv_streams_model_ready_columns(client: TestClient, engine: Engine) -> None:
    """CSV export streams canonical columns (schema order) + lineage columns."""
    tenant_id, job_id = _seed_output(engine)
    resp = client.get(f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/output.csv")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    lines = resp.text.strip().splitlines()
    header = lines[0].split(",")
    # canonical columns first, then lineage columns.
    assert header[:4] == ["date", "channel", "spend", "price_index"]
    assert "mapping_config_version" in header and "rule_set_version" in header
    assert len(lines) == 3  # header + 2 rows
    assert "2026-01-05" in lines[1] and "150" in lines[1]


def test_output_contract_404_without_output(client: TestClient) -> None:
    """A job with no generated output returns 404 for the contract."""
    tenant_id = uuid.uuid4()
    resp = client.get(f"/api/v1/tenants/{tenant_id}/jobs/{uuid.uuid4()}/output/contract")
    assert resp.status_code == 404
