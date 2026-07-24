"""RBAC role-management routes (Phase 19).

Exposes the role→permission matrix and lets an admin assign roles to tenant users.
Deny-by-default; every role change is audited (CC-5/audit, CC-1 tenant-scoped).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.auth.service import Principal
from mmm_os.authz import ROLE_PERMISSIONS, Permission, require_permission
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.models import User
from mmm_os.schemas.rbac import RoleMatrixResponse, SetRoleRequest, UserRoleRead

router = APIRouter(prefix="/api/v1", tags=["rbac"])

_ADMIN = Depends(require_permission(Permission.ADMIN))


@router.get("/rbac/roles", response_model=RoleMatrixResponse)
def role_matrix_route() -> RoleMatrixResponse:
    """Return the role → permission matrix (for the role-management UI)."""
    return RoleMatrixResponse(
        roles={role: sorted(p.value for p in perms) for role, perms in ROLE_PERMISSIONS.items()}
    )


@router.get("/tenants/{tenant_id}/users", response_model=list[UserRoleRead])
def list_users_route(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: Principal | None = _ADMIN,
) -> list[UserRoleRead]:
    """List a tenant's users and their roles."""
    users = session.scalars(
        tenant_scoped_select(User, tenant_id).order_by(User.email)
    ).all()
    return [UserRoleRead.model_validate(u) for u in users]


@router.put("/tenants/{tenant_id}/users/{user_id}/role", response_model=UserRoleRead)
def set_role_route(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    body: SetRoleRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = _ADMIN,
) -> UserRoleRead:
    """Assign a role to a tenant user (admin only, audited)."""
    if body.role not in ROLE_PERMISSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown role {body.role!r}; valid roles: {sorted(ROLE_PERMISSIONS)}",
        )
    user = session.scalar(tenant_scoped_select(User, tenant_id).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    before = user.role
    user.role = body.role
    session.flush()
    record_audit(
        session,
        tenant_id=tenant_id,
        action="rbac.set_role",
        principal=principal,
        target_type="user",
        target_id=str(user_id),
        detail={"from": before, "to": body.role},
    )
    session.commit()
    return UserRoleRead.model_validate(user)
