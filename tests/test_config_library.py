"""Tests for the config library + authorship (Phase 13, Slice 1)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _sheet_id(client: TestClient, tenant_id: uuid.UUID) -> str:
    up = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("d.csv", b"date,channel,spend\n2026-01-01,Facebook,100\n", "text/csv")},
    )
    file_id = up.json()["file"]["id"]
    proc = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    return proc.json()["sheets"][0]["id"]


def test_config_library_lists_mappings_and_rule_sets_with_versions(client: TestClient) -> None:
    """Saved mapping + rule set appear in the library with version counts + history."""
    tenant_id = uuid.uuid4()
    sheet_id = _sheet_id(client, tenant_id)

    # Save a mapping (twice → 2 versions) and a rule set.
    for _ in range(2):
        client.post(
            f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/mapping",
            json={"name": "m", "mapping": {"date": "date", "channel": "channel", "spend": "spend"}},
        )
    client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet_id}/rule-set",
        json={"rules": [{"target_field": "date", "operation": "parse_date"}]},
    )

    lib = client.get(f"/api/v1/tenants/{tenant_id}/config-library")
    assert lib.status_code == 200, lib.text
    items = lib.json()["items"]
    kinds = {i["kind"]: i for i in items}
    assert "mapping" in kinds and "rule_set" in kinds
    assert kinds["mapping"]["version_count"] == 2
    assert kinds["mapping"]["latest_version"] == 2

    # Version history for the mapping family.
    versions = client.get(
        f"/api/v1/tenants/{tenant_id}/config-library/versions",
        params={"kind": "mapping", "key": kinds["mapping"]["key"]},
    )
    assert versions.status_code == 200, versions.text
    body = versions.json()
    assert [v["version"] for v in body["versions"]] == [2, 1]
    assert "columns mapped" in body["versions"][0]["summary"]


def test_config_versions_unknown_404(client: TestClient) -> None:
    """Version history for a non-existent family is a 404."""
    tenant_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/tenants/{tenant_id}/config-library/versions",
        params={"kind": "rule_set", "key": "nope"},
    )
    assert resp.status_code == 404
