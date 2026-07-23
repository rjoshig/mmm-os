"""Integration + service tests for the transformation API and persistence (03.2)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.models import Tenant
from mmm_os.transform.service import (
    resolve_rule_specs,
    save_rule_set_with_rules,
)
from mmm_os.transform.types import RuleSpec


def test_preview_returns_before_and_after(client: TestClient) -> None:
    """Preview applies rules to sample rows and returns before/after (P3-7)."""
    tenant_id = uuid.uuid4()
    body = {
        "rows": [{"channel": "FB", "spend": "100"}, {"channel": "fb_ads", "spend": "50"}],
        "rules": [
            {
                "target_field": "channel",
                "operation": "map_value",
                "params": {"taxonomy": "channel"},
            },
            {"target_field": "spend", "operation": "cast_type", "params": {"to": "number"}},
        ],
    }
    response = client.post(f"/api/v1/tenants/{tenant_id}/transform/preview", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["before"][0]["channel"] == "FB"
    assert {r["channel"] for r in data["after"]} == {"Facebook"}
    assert data["after"][0]["spend"] == 100.0


def test_preview_is_idempotent(client: TestClient) -> None:
    """Re-running the same preview yields identical output (CC-6)."""
    tenant_id = uuid.uuid4()
    body = {
        "rows": [{"spend": "100"}],
        "rules": [{"target_field": "spend", "operation": "cast_type", "params": {"to": "number"}}],
    }
    first = client.post(f"/api/v1/tenants/{tenant_id}/transform/preview", json=body).json()
    second = client.post(f"/api/v1/tenants/{tenant_id}/transform/preview", json=body).json()
    assert first == second


def test_preview_unknown_operation_400(client: TestClient) -> None:
    """An unknown operation is a 400, not a crash."""
    tenant_id = uuid.uuid4()
    body = {"rows": [{"a": 1}], "rules": [{"target_field": "a", "operation": "nope"}]}
    response = client.post(f"/api/v1/tenants/{tenant_id}/transform/preview", json=body)
    assert response.status_code == 400


def test_save_rule_set_versions(client: TestClient) -> None:
    """Saving a rule set twice returns versions 1 then 2."""
    tenant_id = uuid.uuid4()
    body = {
        "name": "defaults",
        "rules": [{"target_field": "date", "operation": "parse_date"}],
    }
    v1 = client.post(f"/api/v1/tenants/{tenant_id}/rule-sets", json=body)
    v2 = client.post(f"/api/v1/tenants/{tenant_id}/rule-sets", json=body)
    assert v1.status_code == 201
    assert v1.json()["version"] == 1
    assert v2.json()["version"] == 2


def _upload_and_process(client: TestClient, tenant_id: uuid.UUID, filename: str) -> str:
    """Upload a CSV with a fixed header and return the resulting sheet id."""
    upload = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={
            "upload": (filename, b"date,channel,spend\n2026-01-01,Facebook,100\n", "text/csv")
        },
    )
    file_id = upload.json()["file"]["id"]
    processed = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
    sheet_id: str = processed.json()["sheets"][0]["id"]
    return sheet_id


def test_rule_set_reused_across_sheets_of_same_signature(client: TestClient) -> None:
    """A rule set saved on one sheet is found by a *different* sheet with identical headers.

    This is the Slice-3 "configure once, reuse forever" property: rule sets are keyed
    by column signature (like mappings), not by ``sheet_id``, so a new file's new sheet
    inherits the rules as long as its columns match (CC-3 config-as-data reuse).
    """
    tenant_id = uuid.uuid4()
    sheet_a = _upload_and_process(client, tenant_id, "file_a.csv")
    sheet_b = _upload_and_process(client, tenant_id, "file_b.csv")
    assert sheet_a != sheet_b  # genuinely different sheets/files

    # No rule set exists for sheet B's signature yet.
    assert (
        client.get(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_b}/rule-set").status_code == 404
    )

    # Save a rule set against sheet A by its column signature.
    save = client.post(
        f"/api/v1/tenants/{tenant_id}/sheets/{sheet_a}/rule-set",
        json={"rules": [{"target_field": "date", "operation": "parse_date"}]},
    )
    assert save.status_code == 201, save.text

    # Sheet B (same headers, different sheet_id) now resolves the same rule set.
    found = client.get(f"/api/v1/tenants/{tenant_id}/sheets/{sheet_b}/rule-set")
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["name"].startswith("sig:")
    assert [r["operation"] for r in body["rules"]] == ["parse_date"]


def test_layered_rule_resolution(engine: Engine) -> None:
    """resolve_rule_specs concatenates rules across layers (global→customer)."""
    with Session(engine) as session:
        tenant = Tenant(name="Acme", slug="acme")
        session.add(tenant)
        session.flush()
        save_rule_set_with_rules(
            session,
            tenant_id=tenant.id,
            name="std",
            layer="global",
            specs=[RuleSpec(target_field="date", operation="parse_date", order=0)],
        )
        save_rule_set_with_rules(
            session,
            tenant_id=tenant.id,
            name="std",
            layer="customer",
            specs=[RuleSpec(target_field="channel", operation="map_value", order=0)],
        )
        specs = resolve_rule_specs(session, tenant.id, "std")
        operations = [s.operation for s in specs]
        assert operations == ["parse_date", "map_value"]
