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


def test_bulk_review_resolves_a_cluster(client: TestClient) -> None:
    """Bulk review resolves many flags at once and ignores foreign ids (Cycle-1)."""
    tenant_id = uuid.uuid4()
    job_id = _make_job(client, tenant_id)
    # Three rows each missing 'channel' → a cluster of required-missing flags.
    rows = [
        {"date": "2026-01-01", "spend": "100"},
        {"date": "2026-01-02", "spend": "110"},
        {"date": "2026-01-03", "spend": "120"},
    ]
    validated = client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/validate",
        json={"rows": rows},
    )
    flags = validated.json()["flags"]
    channel_ids = [
        f["id"] for f in flags if f["location"].get("field") == "channel"
    ]
    assert len(channel_ids) >= 3

    reviewer = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{job_id}/validation-flags/bulk-review",
        # Include a foreign id to prove it is ignored, not applied.
        json={
            "flag_ids": [*channel_ids, str(uuid.uuid4())],
            "status": "resolved",
            "resolved_by": reviewer,
        },
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()["updated"]
    assert len(updated) == len(channel_ids)  # foreign id ignored
    assert all(u["review_status"] == "resolved" for u in updated)
    assert all(u["resolved_by"] == reviewer for u in updated)


def test_bulk_review_unknown_job_404(client: TestClient) -> None:
    """Bulk review against a non-existent job returns 404."""
    tenant_id = uuid.uuid4()
    resp = client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{uuid.uuid4()}/validation-flags/bulk-review",
        json={"flag_ids": [str(uuid.uuid4())], "status": "resolved"},
    )
    assert resp.status_code == 404


def test_validate_unknown_job_404(client: TestClient) -> None:
    """Validating against a non-existent job returns 404."""
    tenant_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/tenants/{tenant_id}/jobs/{uuid.uuid4()}/validate", json={"rows": []}
    )
    assert response.status_code == 404
