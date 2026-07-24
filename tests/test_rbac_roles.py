"""Tests for Phase 19 — RBAC enhancements (approver + platform_admin)."""

from __future__ import annotations

import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from mmm_os.authz import ROLE_PERMISSIONS, Permission, has_permission
from mmm_os.models import User


def test_new_roles_present_with_expected_permissions() -> None:
    assert "approver" in ROLE_PERMISSIONS
    assert "platform_admin" in ROLE_PERMISSIONS
    # Approver can review + approve but NOT author configs (segregation of duties).
    assert has_permission("approver", Permission.APPROVE)
    assert has_permission("approver", Permission.REVIEW)
    assert not has_permission("approver", Permission.WRITE_CONFIG)
    # platform_admin mirrors admin (never exceeds it — 08.1 self-check).
    assert ROLE_PERMISSIONS["platform_admin"] == ROLE_PERMISSIONS["admin"]


def test_member_cannot_approve() -> None:
    assert has_permission("member", Permission.WRITE_CONFIG)
    assert not has_permission("member", Permission.APPROVE)


def test_role_matrix_api(client) -> None:
    resp = client.get("/api/v1/rbac/roles")
    assert resp.status_code == 200
    roles = resp.json()["roles"]
    assert "approve" in roles["approver"]
    assert "write_config" not in roles["approver"]


def test_set_role_api_happy_path(client, engine: Engine) -> None:
    tenant_id = client.post(
        "/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"}
    ).json()["id"]

    # Insert a user directly in the same DB the client uses.
    session = sessionmaker(bind=engine)()
    user = User(tenant_id=uuid.UUID(tenant_id), email="u@x.com", role="viewer")
    session.add(user)
    session.commit()

    resp = client.put(
        f"/api/v1/tenants/{tenant_id}/users/{user.id}/role", json={"role": "approver"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "approver"


def test_set_role_api_rejects_unknown_role(client) -> None:
    tenant_id = client.post(
        "/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"}
    ).json()["id"]
    resp = client.put(
        f"/api/v1/tenants/{tenant_id}/users/{uuid.uuid4()}/role", json={"role": "wizard"}
    )
    assert resp.status_code == 422


def test_least_privilege_no_role_exceeds_admin() -> None:
    admin = ROLE_PERMISSIONS["admin"]
    for role, perms in ROLE_PERMISSIONS.items():
        assert perms <= admin, f"{role} exceeds admin"
