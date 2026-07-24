"""Tenant validation-rule CRUD + the active-rule collector (Part 3)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import ValidationRule
from mmm_os.models.enums import Severity
from mmm_os.services.schema_extension import custom_checks
from mmm_os.validation.custom import ValidationRuleSpec

_SEVERITIES = {Severity.INFO.value, Severity.WARNING.value, Severity.BLOCKING.value}


def create_rule(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    name: str,
    expression: str,
    severity: str = Severity.WARNING.value,
    enabled: bool = True,
    description: str | None = None,
    created_by: uuid.UUID | None = None,
) -> ValidationRule:
    """Create a validation rule. Raises ``ValueError`` on an invalid severity."""
    if severity not in _SEVERITIES:
        raise ValueError(f"severity must be one of {sorted(_SEVERITIES)}")
    rule = ValidationRule(
        tenant_id=tenant_id,
        name=name.strip(),
        expression=expression.strip(),
        severity=severity,
        enabled=enabled,
        description=description,
        created_by=created_by,
    )
    session.add(rule)
    session.flush()
    return rule


def list_rules(session: Session, tenant_id: uuid.UUID) -> list[ValidationRule]:
    """Return a tenant's validation rules (newest first)."""
    return list(
        session.scalars(
            tenant_scoped_select(ValidationRule, tenant_id).order_by(
                ValidationRule.created_at.desc()
            )
        ).all()
    )


def update_rule(
    session: Session,
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    *,
    name: str | None = None,
    expression: str | None = None,
    severity: str | None = None,
    enabled: bool | None = None,
    description: str | None = None,
) -> ValidationRule | None:
    """Update a rule (only provided fields). Raises on an invalid severity."""
    rule = session.scalar(
        tenant_scoped_select(ValidationRule, tenant_id).where(ValidationRule.id == rule_id)
    )
    if rule is None:
        return None
    if severity is not None:
        if severity not in _SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_SEVERITIES)}")
        rule.severity = severity
    if name is not None:
        rule.name = name.strip()
    if expression is not None:
        rule.expression = expression.strip()
    if enabled is not None:
        rule.enabled = enabled
    if description is not None:
        rule.description = description
    session.flush()
    return rule


def delete_rule(session: Session, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
    """Delete a rule; return whether it existed."""
    rule = session.scalar(
        tenant_scoped_select(ValidationRule, tenant_id).where(ValidationRule.id == rule_id)
    )
    if rule is None:
        return False
    session.delete(rule)
    session.flush()
    return True


def active_validation_rules(session: Session, tenant_id: uuid.UUID) -> list[ValidationRuleSpec]:
    """Return the specs to run for a tenant: enabled rules + legacy field checks.

    Unions the first-class ``ValidationRule`` rows (enabled only, each with its own
    severity) with any legacy ``schema_extension.validation`` expressions (Phase 21,
    ``warning`` severity) so existing custom-field checks keep working.
    """
    specs = [
        ValidationRuleSpec(name=r.name, expression=r.expression, severity=r.severity)
        for r in list_rules(session, tenant_id)
        if r.enabled
    ]
    seen = {s.name for s in specs}
    for name, expression in custom_checks(session, tenant_id):
        if name not in seen:
            specs.append(
                ValidationRuleSpec(
                    name=name, expression=expression, severity=Severity.WARNING.value
                )
            )
    return specs
