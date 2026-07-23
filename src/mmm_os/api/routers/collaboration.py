"""Collaboration routes (Phase 13.4): assign review work + the review queue.

Assigning/resolving needs the ``review`` permission; listing needs ``read`` (the
router is behind ``require_auth``). Assignments are tenant-scoped (CC-1) and audited.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.models import Assignment, User
from mmm_os.schemas.collaboration import AssignmentCreate, AssignmentRead

router = APIRouter(prefix="/api/v1", tags=["collaboration"])

_REVIEW = Depends(require_permission(Permission.REVIEW))


def _to_read(assignment: Assignment, emails: dict[uuid.UUID, str]) -> AssignmentRead:
    return AssignmentRead(
        id=assignment.id,
        target_type=assignment.target_type,
        target_id=assignment.target_id,
        assignee_user_id=assignment.assignee_user_id,
        assignee_email=emails.get(assignment.assignee_user_id),
        assigned_by=assignment.assigned_by,
        status=assignment.status,
        note=assignment.note,
        created_at=assignment.created_at,
    )


def _emails(session: Session, tenant_id: uuid.UUID) -> dict[uuid.UUID, str]:
    return {u.id: u.email for u in session.scalars(tenant_scoped_select(User, tenant_id)).all()}


@router.post(
    "/tenants/{tenant_id}/assignments",
    status_code=status.HTTP_201_CREATED,
    response_model=AssignmentRead,
)
def create_assignment(
    tenant_id: uuid.UUID,
    body: AssignmentCreate,
    session: Session = Depends(get_session),
    principal: Principal | None = _REVIEW,
) -> AssignmentRead:
    """Assign a file/sheet to a tenant user for review (Phase 13.4)."""
    assignment = Assignment(
        tenant_id=tenant_id,
        target_type=body.target_type,
        target_id=body.target_id,
        assignee_user_id=body.assignee_user_id,
        assigned_by=principal.user_id if principal else None,
        note=body.note,
    )
    session.add(assignment)
    session.flush()
    record_audit(
        session,
        tenant_id=tenant_id,
        action="assignment.create",
        principal=principal,
        target_type=body.target_type,
        target_id=str(body.target_id),
        detail={"assignee": str(body.assignee_user_id)},
    )
    session.commit()
    return _to_read(assignment, _emails(session, tenant_id))


@router.get("/tenants/{tenant_id}/assignments", response_model=list[AssignmentRead])
def list_assignments(
    tenant_id: uuid.UUID,
    assignee: uuid.UUID | None = None,
    open_only: bool = True,
    session: Session = Depends(get_session),
) -> list[AssignmentRead]:
    """List assignments, newest first; filter by assignee (a user's queue) + status."""
    query = tenant_scoped_select(Assignment, tenant_id).order_by(Assignment.created_at.desc())
    if assignee is not None:
        query = query.where(Assignment.assignee_user_id == assignee)
    if open_only:
        query = query.where(Assignment.status == "open")
    rows = session.scalars(query).all()
    emails = _emails(session, tenant_id)
    return [_to_read(a, emails) for a in rows]


@router.post(
    "/tenants/{tenant_id}/assignments/{assignment_id}/resolve",
    response_model=AssignmentRead,
)
def resolve_assignment(
    tenant_id: uuid.UUID,
    assignment_id: uuid.UUID,
    session: Session = Depends(get_session),
    principal: Principal | None = _REVIEW,
) -> AssignmentRead:
    """Mark an assignment done (Phase 13.4)."""
    assignment = session.scalar(
        tenant_scoped_select(Assignment, tenant_id).where(Assignment.id == assignment_id)
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assignment not found")
    assignment.status = "done"
    record_audit(
        session,
        tenant_id=tenant_id,
        action="assignment.resolve",
        principal=principal,
        target_type="assignment",
        target_id=str(assignment_id),
    )
    session.commit()
    return _to_read(assignment, _emails(session, tenant_id))
