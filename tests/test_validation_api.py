"""Integration tests for the validation API (04.2)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _make_job(client: TestClient, tenant_id: uuid.UUID) -> str:
    upload = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("x.csv", b"date,channel,spend\n2026-01-01,Facebook,1\n", "text/csv")},
    )
    job_id: str = upload.json()["job"]["id"]
    return job_id


def test_validate_acceptance_scenario(client: TestClient) -> None:
    """A spend spike, a duplicate row, and a missing date produce distinct flags."""
    tenant_id = uuid.uuid4()
    job_id = _make_job(client, tenant_id)
    rows = [
        {"date": "2026-01-01", "channel": "Facebook", "spend": "100"},
        {"date": "2026-01-02", "channel": "Facebook", "spend": "110"},
        {"date": "2026-01-03", "channel": "Facebook", "spend": "105"},
        {"date": "2026-01-03", "channel": "Facebook", "spend": "105"},  # duplicate
        {"date": "2026-01-05", "channel": "Facebook", "spend": "500"},  # gap + spike
    ]
    response = client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/validate",
        json={"rows": rows, "anomaly_measure": "spend"},
    )
    assert response.status_code == 200, response.text
    checks = {flag["location"]["check"] for flag in response.json()["flags"]}
    assert {"duplicate_row", "date_gap", "anomaly"} <= checks


def test_blocking_flag_and_review_lifecycle(client: TestClient) -> None:
    """A negative measure blocks; resolving records who/when (P4-5)."""
    tenant_id = uuid.uuid4()
    job_id = _make_job(client, tenant_id)
    response = client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/validate",
        json={"rows": [{"date": "2026-01-01", "channel": "Facebook", "spend": "-5"}]},
    )
    body = response.json()
    assert body["blocked"] is True
    flag_id = body["flags"][0]["id"]

    reviewer = str(uuid.uuid4())
    reviewed = client.post(
        f"/api/v1/tenants/{tenant_id}/validation-flags/{flag_id}/review",
        json={"status": "resolved", "resolved_by": reviewer},
    )
    assert reviewed.status_code == 200
    data = reviewed.json()
    assert data["review_status"] == "resolved"
    assert data["resolved_by"] == reviewer
    assert data["resolved_at"] is not None


def test_list_flags_and_invalid_review(client: TestClient) -> None:
    """Flags are listable; an invalid review status is a 400."""
    tenant_id = uuid.uuid4()
    job_id = _make_job(client, tenant_id)
    client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/validate",
        json={"rows": [{"date": "2026-01-01", "spend": "100"}]},  # missing channel -> flag
    )
    listed = client.get(f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/validation-flags")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    flag_id = listed.json()[0]["id"]
    bad = client.post(
        f"/api/v1/tenants/{tenant_id}/validation-flags/{flag_id}/review",
        json={"status": "nonsense"},
    )
    assert bad.status_code == 400


def test_validate_unknown_job_404(client: TestClient) -> None:
    """Validating against a non-existent job returns 404."""
    tenant_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{uuid.uuid4()}/validate", json={"rows": []}
    )
    assert response.status_code == 404
