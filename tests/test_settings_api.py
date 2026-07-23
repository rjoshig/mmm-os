"""Integration tests for per-tenant reporting settings (Cycle 2, Slice 3)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_settings_defaults_then_update(client: TestClient) -> None:
    """GET returns defaults on first access; PUT persists reporting frame + FX."""
    tenant_id = uuid.uuid4()

    got = client.get(f"/api/v1/tenants/{tenant_id}/settings")
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["reporting_currency"] == "USD"
    assert body["reporting_timezone"] == "UTC"
    assert body["fx_rates"] == {}

    put = client.put(
        f"/api/v1/tenants/{tenant_id}/settings",
        json={
            "reporting_currency": "eur",  # lower-cased input is normalized
            "reporting_timezone": "Europe/Berlin",
            "fx_rates": {"usd": 0.9, "gbp": 1.15, "bad": 0},  # non-positive dropped
        },
    )
    assert put.status_code == 200, put.text
    updated = put.json()
    assert updated["reporting_currency"] == "EUR"
    assert updated["reporting_timezone"] == "Europe/Berlin"
    assert updated["fx_rates"] == {"USD": 0.9, "GBP": 1.15}

    # Persisted across requests.
    again = client.get(f"/api/v1/tenants/{tenant_id}/settings").json()
    assert again["reporting_currency"] == "EUR"
    assert again["fx_rates"] == {"USD": 0.9, "GBP": 1.15}


def test_preview_convert_currency_uses_tenant_reporting_frame(client: TestClient) -> None:
    """A saved reporting frame drives to_reporting convert_currency in preview."""
    tenant_id = uuid.uuid4()
    client.put(
        f"/api/v1/tenants/{tenant_id}/settings",
        json={"reporting_currency": "USD", "fx_rates": {"EUR": 1.1}},
    )
    body = {
        "rows": [{"spend": "100", "currency": "EUR"}],
        "rules": [
            {
                "target_field": "spend",
                "operation": "convert_currency",
                "params": {"to_reporting": True, "currency_field": "currency"},
            }
        ],
    }
    resp = client.post(f"/api/v1/tenants/{tenant_id}/transform/preview", json=body)
    assert resp.status_code == 200, resp.text
    assert round(resp.json()["after"][0]["spend"], 2) == 110.0
