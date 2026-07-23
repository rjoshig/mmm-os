"""Transformation routes: save a rule set and preview rules on sample rows (03.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical, require_auth
from mmm_os.auth.service import Principal
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.models import Sheet
from mmm_os.models.enums import RuleLayer
from mmm_os.schemas.transform import (
    PreviewRequest,
    PreviewResponse,
    RuleSetRead,
    RuleSpecIn,
    SaveRuleSetRequest,
    SaveSheetRuleSetRequest,
)
from mmm_os.services.tenant_settings import reporting_context
from mmm_os.transform.preview import preview as run_preview
from mmm_os.transform.registry import RuleContext, TransformError
from mmm_os.transform.service import (
    get_rule_set,
    load_rule_specs,
    rule_set_name_for_sheet,
    save_rule_set_with_rules,
)
from mmm_os.transform.types import RuleSpec

router = APIRouter(prefix="/api/v1", tags=["transform"])


def _get_sheet(session: Session, tenant_id: uuid.UUID, sheet_id: uuid.UUID) -> Sheet:
    sheet = session.scalar(tenant_scoped_select(Sheet, tenant_id).where(Sheet.id == sheet_id))
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sheet not found")
    return sheet


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
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> PreviewResponse:
    """Return before/after for a rule set on sample rows, persisting nothing (P3-7).

    Args:
        tenant_id: The owning tenant (for taxonomy + reporting context).
        body: The sample rows + rules to preview.
        session: Database session (injected; for the reporting frame).
        canonical: Canonical schema/taxonomies (injected).

    Returns:
        The before and after records.

    Raises:
        HTTPException: 400 if a rule is malformed or uses an unknown operation.
    """
    ctx = RuleContext(
        taxonomies=canonical.taxonomies,
        schema=canonical.schema,
        reporting=reporting_context(session, tenant_id),
    )
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
        created_by=principal.user_id if principal else None,
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


@router.get(
    "/tenants/{tenant_id}/rule-sets/{name}",
    response_model=RuleSetRead,
)
def get_rule_set_route(
    tenant_id: uuid.UUID,
    name: str,
    layer: str = RuleLayer.CUSTOMER.value,
    session: Session = Depends(get_session),
) -> RuleSetRead:
    """Fetch the latest saved version of a named rule set (P3-8).

    Args:
        tenant_id: The owning tenant.
        name: The rule-set's natural-key name.
        layer: The resolution layer to look up (defaults to customer).
        session: Database session (injected).

    Returns:
        The latest version of the named rule set.

    Raises:
        HTTPException: 404 if no rule set with that name/layer exists.
    """
    rule_set = get_rule_set(session, tenant_id, name, layer)
    if rule_set is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule set not found")
    specs = load_rule_specs(session, rule_set)
    return RuleSetRead(
        id=rule_set.id,
        tenant_id=rule_set.tenant_id,
        name=rule_set.name,
        version=rule_set.version,
        layer=rule_set.layer,
        rules=[
            RuleSpecIn(
                target_field=s.target_field,
                operation=s.operation,
                params=s.params,
                condition=s.condition,
                order=s.order,
                layer=s.layer,
            )
            for s in specs
        ],
    )


@router.get(
    "/tenants/{tenant_id}/sheets/{sheet_id}/rule-set",
    response_model=RuleSetRead,
)
def get_sheet_rule_set_route(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> RuleSetRead:
    """Fetch the latest rule set matching a sheet's column signature.

    Rule sets are reused across files with identical headers (keyed by column
    signature, not ``sheet_id``), so a rule set saved for one sheet applies to any
    sheet with the same column structure.

    Raises:
        HTTPException: 404 if the sheet or a matching rule set is not found.
    """
    sheet = _get_sheet(session, tenant_id, sheet_id)
    rule_set = get_rule_set(session, tenant_id, rule_set_name_for_sheet(sheet))
    if rule_set is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule set not found")
    specs = load_rule_specs(session, rule_set)
    return RuleSetRead(
        id=rule_set.id,
        tenant_id=rule_set.tenant_id,
        name=rule_set.name,
        version=rule_set.version,
        layer=rule_set.layer,
        rules=[
            RuleSpecIn(
                target_field=s.target_field,
                operation=s.operation,
                params=s.params,
                condition=s.condition,
                order=s.order,
                layer=s.layer,
            )
            for s in specs
        ],
    )


@router.post(
    "/tenants/{tenant_id}/sheets/{sheet_id}/rule-set",
    response_model=RuleSetRead,
    status_code=status.HTTP_201_CREATED,
)
def save_sheet_rule_set_route(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    body: SaveSheetRuleSetRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = Depends(require_auth),
) -> RuleSetRead:
    """Save (version) a rule set under the sheet's column-signature name.

    Because the name is derived from the column signature, the saved rules are
    reused by every sheet/file with the same headers — the "configure once, reuse
    forever" property (mirrors mapping configs).
    """
    sheet = _get_sheet(session, tenant_id, sheet_id)
    name = rule_set_name_for_sheet(sheet)
    rule_set = save_rule_set_with_rules(
        session,
        tenant_id=tenant_id,
        name=name,
        layer=body.layer,
        specs=[_to_spec(r) for r in body.rules],
        created_by=principal.user_id if principal else None,
        lifecycle_status="draft" if body.draft else "published",
    )
    record_audit(
        session,
        tenant_id=tenant_id,
        action="ruleset.save",
        principal=principal,
        target_type="rule_set",
        target_id=str(rule_set.id),
        detail={"version": rule_set.version, "rules": len(body.rules), "by_signature": True},
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
