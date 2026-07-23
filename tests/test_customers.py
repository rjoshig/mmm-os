"""Tests for customer / workspace management (Cycle 7, Slice 7.1)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_onboard_list_and_get_customer(client: TestClient) -> None:
    """A customer can be onboarded, listed, and fetched; slug is derived + unique."""
    created = client.post(
        "/api/v1/customers",
        json={"name": "Walmart", "tier": "enterprise", "region": "us"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["slug"] == "walmart"  # derived from name
    assert body["tier"] == "enterprise"
    customer_id = body["id"]

    listing = client.get("/api/v1/customers")
    assert listing.status_code == 200
    assert any(c["id"] == customer_id for c in listing.json())

    got = client.get(f"/api/v1/customers/{customer_id}")
    assert got.status_code == 200
    assert got.json()["name"] == "Walmart"


def test_duplicate_slug_conflicts(client: TestClient) -> None:
    """Onboarding two customers that slugify to the same slug is a 409."""
    first = client.post("/api/v1/customers", json={"name": "Ace Hardware"})
    assert first.status_code == 201
    dup = client.post("/api/v1/customers", json={"name": "ace hardware"})
    assert dup.status_code == 409


def test_bad_tier_rejected(client: TestClient) -> None:
    """An invalid tier is rejected (422)."""
    resp = client.post("/api/v1/customers", json={"name": "X", "tier": "platinum"})
    assert resp.status_code == 422
