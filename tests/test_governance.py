"""Tests for Phase-8 RBAC + audit log (and the Phase-08.1 access review)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mmm_os.api import deps
from mmm_os.auth.hashing import hash_password
from mmm_os.auth.service import seed_default_admin
from mmm_os.authz import ROLE_PERMISSIONS, Permission, has_permission
from mmm_os.core.config import Settings
from mmm_os.models import AuditLog, User


def _seed_admin(engine: Engine) -> uuid.UUID:
    with Session(engine) as db:
        admin = seed_default_admin(db, Settings())
        db.commit()
        return admin.tenant_id


def _add_viewer(engine: Engine, tenant_id: uuid.UUID) -> None:
    with Session(engine) as db:
        pw, salt = hash_password("view123")
        db.add(
            User(
                tenant_id=tenant_id,
                email="viewer",
                role="viewer",
                status="active",
                password_hash=pw,
                password_salt=salt,
            )
        )
        db.commit()


def test_role_permission_matrix() -> None:
    """The matrix is least-privilege: viewer read-only, member no admin, admin all."""
    assert has_permission("admin", Permission.ADMIN)
    assert has_permission("member", Permission.WRITE_CONFIG)
    assert not has_permission("member", Permission.ADMIN)
    assert ROLE_PERMISSIONS["viewer"] == frozenset({Permission.READ})
    assert not has_permission("nobody", Permission.READ)


def test_login_is_audited(client: TestClient, engine: Engine) -> None:
    """A successful login writes an audit entry (P8-2)."""
    tid = _seed_admin(engine)
    client.post("/api/v1/auth/login", json={"email": "admin", "password": "admin123"})

    with Session(engine) as db:
        entries = db.scalars(select(AuditLog).where(AuditLog.action == "auth.login")).all()
        assert len(entries) == 1
        assert entries[0].tenant_id == tid


def test_admin_endpoints_list_users_and_audit(client: TestClient, engine: Engine) -> None:
    """Admin endpoints return users, the audit log, and an access review."""
    tid = _seed_admin(engine)
    client.post("/api/v1/auth/login", json={"email": "admin", "password": "admin123"})

    users = client.get(f"/api/v1/tenants/{tid}/users")
    assert users.status_code == 200
    assert {u["email"] for u in users.json()} == {"admin"}

    audit = client.get(f"/api/v1/tenants/{tid}/audit-log")
    assert audit.status_code == 200 and audit.json()[0]["action"] == "auth.login"

    review = client.get(f"/api/v1/tenants/{tid}/access-review")
    assert review.status_code == 200
    assert "admin" in review.json()[0]["permissions"]


def test_viewer_is_denied_admin_endpoints_when_enabled(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With auth enabled, a viewer gets 403 on admin routes; an admin gets 200."""
    tid = _seed_admin(engine)
    _add_viewer(engine, tid)
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(auth_enabled=True))

    def token_for(email: str, password: str) -> str:
        return client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        ).json()["token"]

    viewer = token_for("viewer", "view123")
    admin = token_for("admin", "admin123")

    denied = client.get(
        f"/api/v1/tenants/{tid}/users", headers={"Authorization": f"Bearer {viewer}"}
    )
    assert denied.status_code == 403

    allowed = client.get(
        f"/api/v1/tenants/{tid}/users", headers={"Authorization": f"Bearer {admin}"}
    )
    assert allowed.status_code == 200
