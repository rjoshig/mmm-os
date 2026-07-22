"""Integration tests for the mapping API (02.2)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _upload_and_process(client: TestClient, tenant_id: uuid.UUID, name: str, content: bytes) -> str:
    upload = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": (name, content, "text/csv")},
    )
    file_id = upload.json()["file"]["id"]
    processed = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    sheet_id: str = processed.json()["sheets"][0]["id"]
    return sheet_id


def test_save_then_automap_same_signature(client: TestClient) -> None:
    """Save a mapping once; a same-structure sheet auto-applies it."""
    tenant_id = uuid.uuid4()
    sheet_a = _upload_and_process(
        client, tenant_id, "a.csv", b"date,channel,spend\n2026-01-01,Facebook,100\n"
    )
    save = client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet_a}/mapping",
        json={"name": "std", "mapping": {"date": "date", "channel": "channel", "spend": "spend"}},
    )
    assert save.status_code == 201, save.text
    assert save.json()["config"]["version"] == 1
    assert save.json()["validation"]["is_complete"]

    sheet_b = _upload_and_process(
        client, tenant_id, "b.csv", b"date,channel,spend\n2026-02-01,Google,200\n"
    )
    auto = client.post(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_b}/automap")
    assert auto.status_code == 200
    body = auto.json()
    assert body["matched"] is True
    assert body["validation"]["is_complete"]
    assert body["mapping"]["spend"] == "spend"


def test_automap_no_match_flags_needs_mapping(client: TestClient) -> None:
    """A sheet with an unseen signature does not match."""
    tenant_id = uuid.uuid4()
    sheet = _upload_and_process(
        client, tenant_id, "c.csv", b"date,channel,impressions\n2026-01-01,TikTok,5000\n"
    )
    auto = client.post(f"/api/v1/tenants/{tenant_id}/sheets/{sheet}/automap")
    assert auto.status_code == 200
    assert auto.json()["matched"] is False
    assert auto.json()["validation"] is None


def test_save_incomplete_mapping_is_flagged(client: TestClient) -> None:
    """A mapping missing a required field is reported incomplete."""
    tenant_id = uuid.uuid4()
    sheet = _upload_and_process(
        client, tenant_id, "d.csv", b"date,channel,spend\n2026-01-01,Facebook,100\n"
    )
    save = client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet}/mapping",
        json={"name": "partial", "mapping": {"date": "date", "spend": "spend"}},
    )
    assert save.status_code == 201
    validation = save.json()["validation"]
    assert validation["is_complete"] is False
    assert "channel" in validation["missing_required"]


def test_remap_creates_new_version(client: TestClient) -> None:
    """Saving twice yields versions 1 then 2 (prior versions retained)."""
    tenant_id = uuid.uuid4()
    sheet = _upload_and_process(
        client, tenant_id, "e.csv", b"date,channel,spend\n2026-01-01,Facebook,100\n"
    )
    full = {"date": "date", "channel": "channel", "spend": "spend"}
    v1 = client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet}/mapping", json={"name": "m", "mapping": full}
    )
    v2 = client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet}/mapping", json={"name": "m", "mapping": full}
    )
    assert v1.json()["config"]["version"] == 1
    assert v2.json()["config"]["version"] == 2


def test_mapping_unknown_sheet_404(client: TestClient) -> None:
    """Auto-mapping a non-existent sheet returns 404."""
    tenant_id = uuid.uuid4()
    response = client.post(f"/api/v1/tenants/{tenant_id}/sheets/{uuid.uuid4()}/automap")
    assert response.status_code == 404
