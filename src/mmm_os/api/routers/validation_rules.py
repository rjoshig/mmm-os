"""Custom validation-rule routes (Part 3): tenant-authored semantic checks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.schemas.validation_rule import (
    ValidationRuleCreate,
    ValidationRuleRead,
    ValidationRuleUpdate,
)
from mmm_os.services.validation_rule import (
    create_rule,
    delete_rule,
    list_rules,
    update_rule,
)

router = APIRouter(prefix="/api/v1", tags=["validation-rules"])

_WRITE_CONFIG = Depends(require_permission(Permission.WRITE_CONFIG))


def _pid(principal: Principal | None) -> uuid.UUID | None:
    return principal.user_id if principal else None


@router.get("/tenants/{tenant_id}/validation-rules", response_model=list[ValidationRuleRead])
def list_rules_route(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[ValidationRuleRead]:
    """List a tenant's custom validation rules."""
    return [ValidationRuleRead.model_validate(r) for r in list_rules(session, tenant_id)]


@router.post(
    "/tenants/{tenant_id}/validation-rules",
    response_model=ValidationRuleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_rule_route(
    tenant_id: uuid.UUID,
    body: ValidationRuleCreate,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> ValidationRuleRead:
    """Create a custom validation rule (sandboxed expression, per-rule severity)."""
    try:
        rule = create_rule(
            session,
            tenant_id,
            name=body.name,
            expression=body.expression,
            severity=body.severity,
            enabled=body.enabled,
            description=body.description,
            created_by=_pid(principal),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    record_audit(
        session,
        tenant_id=tenant_id,
        action="validation_rule.create",
        principal=principal,
        target_type="validation_rule",
        target_id=str(rule.id),
        detail={"name": rule.name, "severity": rule.severity},
    )
    session.commit()
    return ValidationRuleRead.model_validate(rule)


@router.patch(
    "/tenants/{tenant_id}/validation-rules/{rule_id}", response_model=ValidationRuleRead
)
def update_rule_route(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: ValidationRuleUpdate,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> ValidationRuleRead:
    """Update a rule (rename, edit expression, change severity, enable/disable)."""
    try:
        rule = update_rule(
            session,
            tenant_id,
            rule_id,
            name=body.name,
            expression=body.expression,
            severity=body.severity,
            enabled=body.enabled,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")
    record_audit(
        session,
        tenant_id=tenant_id,
        action="validation_rule.update",
        principal=principal,
        target_type="validation_rule",
        target_id=str(rule_id),
        detail={"enabled": rule.enabled, "severity": rule.severity},
    )
    session.commit()
    return ValidationRuleRead.model_validate(rule)


@router.delete(
    "/tenants/{tenant_id}/validation-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_rule_route(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> None:
    """Delete a validation rule."""
    if not delete_rule(session, tenant_id, rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")
    record_audit(
        session,
        tenant_id=tenant_id,
        action="validation_rule.delete",
        principal=principal,
        target_type="validation_rule",
        target_id=str(rule_id),
        detail={},
    )
    session.commit()
