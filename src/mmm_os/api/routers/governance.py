"""Governance/admin + compliance routes (Phases 8 / 08.1).

Admin-only (``Permission.ADMIN``): list tenant users, read the audit log, and run
an access review. When auth is disabled (dev), the permission check is a no-op.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_storage
from mmm_os.auth.service import Principal
from mmm_os.authz import ROLE_PERMISSIONS, Permission, require_permission
from mmm_os.core.config import Settings, get_settings
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.governance.retention import RetentionPolicy, run_retention
from mmm_os.models import AuditLog, User
from mmm_os.models.mixins import utcnow
from mmm_os.schemas.governance import (
    AccessReviewRow,
    AuditEntryRead,
    RetentionPolicyRead,
    RetentionRunResponse,
    UserRead,
)
from mmm_os.storage import ObjectStorage

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


@router.get(
    "/tenants/{tenant_id}/retention/policy",
    response_model=RetentionPolicyRead,
    dependencies=[_ADMIN],
)
def retention_policy(
    tenant_id: uuid.UUID,
    settings: Settings = Depends(get_settings),
) -> RetentionPolicyRead:
    """Return the configured retention windows per data class (Phase 10, P10-1)."""
    policy = RetentionPolicy.from_settings(settings)
    return RetentionPolicyRead(
        raw_file_days=policy.raw_file_days,
        llm_usage_days=policy.llm_usage_days,
        sync_run_days=policy.sync_run_days,
        notification_days=policy.notification_days,
        audit_log_days=policy.audit_log_days,
    )


@router.post(
    "/tenants/{tenant_id}/retention/run",
    response_model=RetentionRunResponse,
    dependencies=[_ADMIN],
)
def retention_run(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
    principal: Principal | None = _ADMIN,
) -> RetentionRunResponse:
    """Purge data past its retention window across all tenants (admin; Phase 10).

    Idempotent (CC-6): only removes what is now expired. A raw file's purge cascades
    its derived data + immutable-raw bytes (the governance exception to CC-2). Audited.
    """
    purged = run_retention(
        session, storage, now=utcnow(), policy=RetentionPolicy.from_settings(settings)
    )
    record_audit(
        session,
        tenant_id=tenant_id,
        action="retention.run",
        principal=principal,
        target_type="tenant",
        target_id=str(tenant_id),
        detail=purged,
    )
    session.commit()
    return RetentionRunResponse(purged=purged)
