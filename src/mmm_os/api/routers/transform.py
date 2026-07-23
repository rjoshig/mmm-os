"""Transformation routes: save a rule set and preview rules on sample rows (03.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical, require_auth
from mmm_os.auth.service import Principal
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.schemas.transform import (
    PreviewRequest,
    PreviewResponse,
    RuleSetRead,
    RuleSpecIn,
    SaveRuleSetRequest,
)
from mmm_os.transform.preview import preview as run_preview
from mmm_os.transform.registry import RuleContext, TransformError
from mmm_os.transform.service import save_rule_set_with_rules
from mmm_os.transform.types import RuleSpec

router = APIRouter(prefix="/api/v1", tags=["transform"])


def _to_spec(rule: RuleSpecIn) -> RuleSpec:
    return RuleSpec(
        target_field=rule.target_field,
        operation=rule.operation,
        params=rule.params,
        condition=rule.condition,
        order=rule.order,
        layer=rule.layer,
    )


@router.post(
    "/tenants/{tenant_id}/transform/preview",
    response_model=PreviewResponse,
)
def preview_rules(
    tenant_id: uuid.UUID,
    body: PreviewRequest,
    canonical: CanonicalConfig = Depends(get_canonical),
) -> PreviewResponse:
    """Return before/after for a rule set on sample rows, persisting nothing (P3-7).

    Args:
        tenant_id: The owning tenant (for taxonomy context).
        body: The sample rows + rules to preview.
        canonical: Canonical schema/taxonomies (injected).

    Returns:
        The before and after records.

    Raises:
        HTTPException: 400 if a rule is malformed or uses an unknown operation.
    """
    ctx = RuleContext(taxonomies=canonical.taxonomies)
    try:
        result = run_preview(body.rows, [_to_spec(r) for r in body.rules], ctx, limit=body.limit)
    except TransformError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PreviewResponse(before=result.before, after=result.after)


@router.post(
    "/tenants/{tenant_id}/rule-sets",
    status_code=status.HTTP_201_CREATED,
    response_model=RuleSetRead,
)
def save_rule_set_route(
    tenant_id: uuid.UUID,
    body: SaveRuleSetRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = Depends(require_auth),
) -> RuleSetRead:
    """Save (version) a rule set and its ordered rules (P3-8).

    Args:
        tenant_id: The owning tenant.
        body: The rule-set payload.
        session: Database session (injected).
        principal: The authenticated actor (recorded in the audit log).

    Returns:
        The saved rule set.
    """
    rule_set = save_rule_set_with_rules(
        session,
        tenant_id=tenant_id,
        name=body.name,
        layer=body.layer,
        specs=[_to_spec(r) for r in body.rules],
    )
    record_audit(
        session,
        tenant_id=tenant_id,
        action="ruleset.save",
        principal=principal,
        target_type="rule_set",
        target_id=str(rule_set.id),
        detail={"version": rule_set.version, "rules": len(body.rules)},
    )
    session.commit()
    return RuleSetRead(
        id=rule_set.id,
        tenant_id=rule_set.tenant_id,
        name=rule_set.name,
        version=rule_set.version,
        layer=rule_set.layer,
        rules=body.rules,
    )
