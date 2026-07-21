"""Smoke tests for the Phase-0 scaffold."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mmm_os.api.main import app


def test_health_ok() -> None:
    """The health route returns a 200 with an ok status."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
