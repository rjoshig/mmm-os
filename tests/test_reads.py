"""Tests for the Phase-6 read endpoints (list/detail over files, sheets, jobs)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _upload_and_process(client: TestClient, tenant_id: uuid.UUID) -> tuple[str, str]:
    content = b"date,channel,spend\n2026-01-01,Facebook,100\n2026-01-02,Google,200\n"
    up = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("data.csv", content, "text/csv")},
    )
    assert up.status_code == 201, up.text
    file_id: str = up.json()["file"]["id"]
    proc = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    assert proc.status_code == 200, proc.text
    return file_id, proc.json()["sheets"][0]["id"]


def test_list_files_and_detail(client: TestClient) -> None:
    """Listing returns the uploaded file with status + sheet count; detail has sheets."""
    tenant_id = uuid.uuid4()
    file_id, _ = _upload_and_process(client, tenant_id)

    listing = client.get(f"/api/v1/tenants/{tenant_id}/files")
    assert listing.status_code == 200, listing.text
    items = listing.json()
    assert len(items) == 1
    assert items[0]["file"]["id"] == file_id
    assert items[0]["latest_job_status"] == "succeeded"
    assert items[0]["sheet_count"] == 1

    detail = client.get(f"/api/v1/tenants/{tenant_id}/files/{file_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert len(body["sheets"]) == 1
    assert body["latest_job"]["status"] == "succeeded"


def test_sheet_detail_has_profile(client: TestClient) -> None:
    """Sheet detail returns the sheet plus its profile (row_count present)."""
    tenant_id = uuid.uuid4()
    _, sheet_id = _upload_and_process(client, tenant_id)

    resp = client.get(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sheet"]["id"] == sheet_id
    assert body["profile"] is not None
    assert body["profile"]["row_count"] == 2


def test_canonical_fields(client: TestClient) -> None:
    """The canonical-fields endpoint lists dimensions + measures for the mapping UI."""
    resp = client.get("/api/v1/canonical/fields")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {f["name"] for f in body["fields"]}
    assert {"date", "channel", "spend"} <= names
    kinds = {f["name"]: f["kind"] for f in body["fields"]}
    assert kinds["date"] == "dimension"
    assert kinds["spend"] == "measure"
    # MMM factor fields are mappable targets too (Cycle 2).
    assert kinds["price_index"] == "factor"
    assert {"price_index", "is_holiday", "seasonality_index"} <= names
    assert body["min_measures_required"] >= 1


def test_sheet_rows_returns_real_data(client: TestClient) -> None:
    """The rows endpoint returns real data rows keyed by column name (below header)."""
    tenant_id = uuid.uuid4()
    _, sheet_id = _upload_and_process(client, tenant_id)
    resp = client.get(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/rows?limit=10")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["columns"] == ["date", "channel", "spend"]
    assert body["rows"][0] == {"date": "2026-01-01", "channel": "Facebook", "spend": "100"}
    assert len(body["rows"]) == 2


def test_reads_are_tenant_scoped(client: TestClient) -> None:
    """A different tenant sees none of the first tenant's files; unknown ids 404."""
    tenant_id = uuid.uuid4()
    other = uuid.uuid4()
    file_id, sheet_id = _upload_and_process(client, tenant_id)

    assert client.get(f"/api/v1/tenants/{other}/files").json() == []
    assert client.get(f"/api/v1/tenants/{other}/files/{file_id}").status_code == 404
    assert client.get(f"/api/v1/tenants/{other}/sheets/{sheet_id}").status_code == 404
