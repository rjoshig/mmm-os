"""Audit-log service (Phase 8, P8-2).

``record_audit`` appends a tamper-evident-by-convention (append-only) entry for a
sensitive action. It is a no-op-safe helper: callers pass the resolved principal
(which may be ``None`` when auth is disabled), so wiring it into a route is a
single line.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from mmm_os.auth.service import Principal
from mmm_os.models import AuditLog


def record_audit(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    action: str,
    principal: Principal | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an audit entry for ``action`` and return it (not committed).

    The caller commits as part of its own transaction so the audit entry and the
    action it records land together.
    """
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=principal.user_id if principal is not None else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    session.add(entry)
    session.flush()
    return entry
