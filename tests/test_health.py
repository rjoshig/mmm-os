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


def test_unhandled_error_returns_json_500_with_cors_headers() -> None:
    """An unhandled server error is JSON and still carries CORS headers.

    Without the catch-all handler, Starlette's 500 bypasses CORSMiddleware, so the
    browser reports "cannot reach the API" instead of the real error. A temporary
    boom route exercises the handler.
    """

    @app.get("/_boom_test")
    def _boom() -> None:
        raise RuntimeError("boom")

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/_boom_test", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal Server Error"
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    finally:
        # Remove the throwaway route so it can't leak into other tests.
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", None) != "/_boom_test"
        ]
