"""Tests for authentication (Phase 00.5, CC-11)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.api import deps
from mmm_os.auth.service import (
    authenticate,
    create_session,
    resolve_session,
    revoke_session,
    seed_default_admin,
)
from mmm_os.core.config import Settings
from mmm_os.secrets import SecretStore


def _seed(engine: Engine) -> None:
    with Session(engine) as db:
        seed_default_admin(db, Settings())
        db.commit()


def test_password_auth_and_sessions(engine: Engine, secret_store: SecretStore) -> None:
    """Seeded admin authenticates; sessions resolve and revoke (pepper via store)."""
    _seed(engine)
    with Session(engine) as db:
        assert authenticate(db, email="admin", password="wrong") is None
        user = authenticate(db, email="admin", password="admin123")
        assert user is not None and user.role == "admin"

        token = create_session(db, secret_store, user=user, ttl_hours=12)
        db.commit()

        principal = resolve_session(db, secret_store, token=token)
        assert principal is not None and principal.email == "admin"

        assert revoke_session(db, secret_store, token=token) is True
        assert resolve_session(db, secret_store, token=token) is None


def test_login_me_logout_endpoints(client: TestClient, engine: Engine) -> None:
    """login issues a token; /me returns the principal; logout revokes it."""
    _seed(engine)

    bad = client.post("/api/v1/auth/login", json={"email": "admin", "password": "nope"})
    assert bad.status_code == 401

    ok = client.post("/api/v1/auth/login", json={"email": "admin", "password": "admin123"})
    assert ok.status_code == 200, ok.text
    token = ok.json()["token"]
    assert ok.json()["principal"]["email"] == "admin"

    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["role"] == "admin"

    assert client.get("/api/v1/auth/me").status_code == 401

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_protected_routes_enforced_when_enabled(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With auth enabled, feature routes require a valid Bearer token (CC-11)."""
    _seed(engine)
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(auth_enabled=True))

    import uuid

    tid = uuid.uuid4()
    assert client.get(f"/api/v1/tenants/{tid}/files").status_code == 401

    token = client.post(
        "/api/v1/auth/login", json={"email": "admin", "password": "admin123"}
    ).json()["token"]
    ok = client.get(f"/api/v1/tenants/{tid}/files", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
