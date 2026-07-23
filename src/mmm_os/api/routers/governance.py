"""Governance/admin + compliance routes (Phases 8 / 08.1).

Admin-only (``Permission.ADMIN``): list tenant users, read the audit log, and run
an access review. When auth is disabled (dev), the permission check is a no-op.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mmm_os.authz import ROLE_PERMISSIONS, Permission, require_permission
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.models import AuditLog, User
from mmm_os.schemas.governance import AccessReviewRow, AuditEntryRead, UserRead

router = APIRouter(prefix="/api/v1", tags=["governance"])

_ADMIN = Depends(require_permission(Permission.ADMIN))


@router.get(
    "/tenants/{tenant_id}/users",
    response_model=list[UserRead],
    dependencies=[_ADMIN],
)
def list_users(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[UserRead]:
    """List the tenant's users (admin only, P8-5)."""
    users = session.scalars(tenant_scoped_select(User, tenant_id).order_by(User.email)).all()
    return [UserRead.model_validate(u) for u in users]


@router.get(
    "/tenants/{tenant_id}/audit-log",
    response_model=list[AuditEntryRead],
    dependencies=[_ADMIN],
)
def read_audit_log(
    tenant_id: uuid.UUID,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[AuditEntryRead]:
    """Return recent audit-log entries, newest first (admin only, P8-2)."""
    entries = session.scalars(
        tenant_scoped_select(AuditLog, tenant_id).order_by(AuditLog.created_at.desc()).limit(limit)
    ).all()
    return [AuditEntryRead.model_validate(e) for e in entries]


@router.get(
    "/tenants/{tenant_id}/access-review",
    response_model=list[AccessReviewRow],
    dependencies=[_ADMIN],
)
def access_review(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[AccessReviewRow]:
    """List each user's role + effective permissions for review (Phase 08.1)."""
    users = session.scalars(tenant_scoped_select(User, tenant_id).order_by(User.email)).all()
    return [
        AccessReviewRow(
            user_id=u.id,
            email=u.email,
            role=u.role,
            permissions=sorted(p.value for p in ROLE_PERMISSIONS.get(u.role, frozenset())),
        )
        for u in users
    ]
