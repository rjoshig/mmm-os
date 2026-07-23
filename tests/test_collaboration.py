"""Tests for work assignment / review queue (Phase 13.4)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.models import Tenant, User


def _tenant_with_user(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    with Session(engine) as session:
        tenant = Tenant(name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        session.flush()
        user = User(tenant_id=tenant.id, email="reviewer@acme.test", role="member")
        session.add(user)
        session.commit()
        return tenant.id, user.id


def test_assign_list_queue_and_resolve(client: TestClient, engine: Engine) -> None:
    """Assign a file to a user, see it in their queue, then resolve it."""
    tenant_id, user_id = _tenant_with_user(engine)
    target = uuid.uuid4()  # stands in for a file id

    created = client.post(
        f"/api/v1/tenants/{tenant_id}/assignments",
        json={
            "target_type": "file",
            "target_id": str(target),
            "assignee_user_id": str(user_id),
            "note": "please review mapping",
        },
    )
    assert created.status_code == 201, created.text
    assignment_id = created.json()["id"]
    assert created.json()["assignee_email"] == "reviewer@acme.test"

    # The assignee's open queue contains it.
    queue = client.get(
        f"/api/v1/tenants/{tenant_id}/assignments", params={"assignee": str(user_id)}
    )
    assert queue.status_code == 200, queue.text
    assert [a["id"] for a in queue.json()] == [assignment_id]

    # Resolve → no longer in the open queue.
    resolved = client.post(f"/api/v1/tenants/{tenant_id}/assignments/{assignment_id}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "done"

    after = client.get(
        f"/api/v1/tenants/{tenant_id}/assignments", params={"assignee": str(user_id)}
    )
    assert after.json() == []


def test_assignment_target_type_validated(client: TestClient, engine: Engine) -> None:
    """An invalid target_type is rejected (422)."""
    tenant_id, user_id = _tenant_with_user(engine)
    resp = client.post(
        f"/api/v1/tenants/{tenant_id}/assignments",
        json={
            "target_type": "bogus",
            "target_id": str(uuid.uuid4()),
            "assignee_user_id": str(user_id),
        },
    )
    assert resp.status_code == 422


def test_resolve_unknown_assignment_404(client: TestClient) -> None:
    """Resolving a non-existent assignment is a 404."""
    tenant_id = uuid.uuid4()
    resp = client.post(f"/api/v1/tenants/{tenant_id}/assignments/{uuid.uuid4()}/resolve")
    assert resp.status_code == 404
