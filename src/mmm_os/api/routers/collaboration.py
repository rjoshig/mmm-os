"""Collaboration routes (Phase 13.4/13.5): review queue, comments, notifications.

Assigning/resolving needs the ``review`` permission; listing needs ``read`` (the
router is behind ``require_auth``). Assignments are tenant-scoped (CC-1) and audited.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import require_auth
from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.models import Assignment, Comment, Notification, User
from mmm_os.schemas.collaboration import (
    AssignmentCreate,
    AssignmentRead,
    CommentCreate,
    CommentRead,
    NotificationRead,
)

router = APIRouter(prefix="/api/v1", tags=["collaboration"])

_REVIEW = Depends(require_permission(Permission.REVIEW))


def _notify(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    recipient: uuid.UUID,
    kind: str,
    message: str,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
) -> None:
    """Create an in-app notification for a user (the pluggable sink is in-app for now)."""
    session.add(
        Notification(
            tenant_id=tenant_id,
            recipient_user_id=recipient,
            kind=kind,
            target_type=target_type,
            target_id=target_id,
            message=message,
        )
    )


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
    _notify(
        session,
        tenant_id=tenant_id,
        recipient=body.assignee_user_id,
        kind="assignment",
        message=f"You were assigned a {body.target_type} to review.",
        target_type=body.target_type,
        target_id=body.target_id,
    )
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


@router.post(
    "/tenants/{tenant_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentRead,
)
def create_comment(
    tenant_id: uuid.UUID,
    body: CommentCreate,
    session: Session = Depends(get_session),
    principal: Principal | None = Depends(require_auth),
) -> CommentRead:
    """Post a comment on an object; @mentions notify the mentioned teammates (13.5)."""
    comment = Comment(
        tenant_id=tenant_id,
        target_type=body.target_type,
        target_id=body.target_id,
        author_user_id=principal.user_id if principal else None,
        body=body.body,
    )
    session.add(comment)
    session.flush()
    for mentioned in set(body.mentions):
        _notify(
            session,
            tenant_id=tenant_id,
            recipient=mentioned,
            kind="mention",
            message="You were mentioned in a comment.",
            target_type=body.target_type,
            target_id=body.target_id,
        )
    session.commit()
    emails = _emails(session, tenant_id)
    return CommentRead(
        id=comment.id,
        target_type=comment.target_type,
        target_id=comment.target_id,
        author_user_id=comment.author_user_id,
        author_email=emails.get(comment.author_user_id) if comment.author_user_id else None,
        body=comment.body,
        created_at=comment.created_at,
    )


@router.get("/tenants/{tenant_id}/comments", response_model=list[CommentRead])
def list_comments(
    tenant_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[CommentRead]:
    """List comments on an object, oldest first (the activity feed)."""
    rows = session.scalars(
        tenant_scoped_select(Comment, tenant_id)
        .where(Comment.target_type == target_type, Comment.target_id == target_id)
        .order_by(Comment.created_at)
    ).all()
    emails = _emails(session, tenant_id)
    return [
        CommentRead(
            id=c.id,
            target_type=c.target_type,
            target_id=c.target_id,
            author_user_id=c.author_user_id,
            author_email=emails.get(c.author_user_id) if c.author_user_id else None,
            body=c.body,
            created_at=c.created_at,
        )
        for c in rows
    ]


@router.get("/tenants/{tenant_id}/notifications", response_model=list[NotificationRead])
def list_notifications(
    tenant_id: uuid.UUID,
    recipient: uuid.UUID | None = None,
    unread_only: bool = False,
    session: Session = Depends(get_session),
) -> list[NotificationRead]:
    """List a recipient's in-app notifications, newest first."""
    query = tenant_scoped_select(Notification, tenant_id).order_by(Notification.created_at.desc())
    if recipient is not None:
        query = query.where(Notification.recipient_user_id == recipient)
    if unread_only:
        query = query.where(Notification.read.is_(False))
    return [
        NotificationRead.model_validate(n, from_attributes=True)
        for n in session.scalars(query)
    ]


@router.post(
    "/tenants/{tenant_id}/notifications/{notification_id}/read",
    response_model=NotificationRead,
)
def mark_notification_read(
    tenant_id: uuid.UUID,
    notification_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> NotificationRead:
    """Mark a notification read."""
    notification = session.scalar(
        tenant_scoped_select(Notification, tenant_id).where(Notification.id == notification_id)
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    notification.read = True
    session.commit()
    return NotificationRead.model_validate(notification, from_attributes=True)
