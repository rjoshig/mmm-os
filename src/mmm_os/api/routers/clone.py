"""Universal clone / duplicate routes (Phase 15)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.schemas.clone import CloneRequest, CloneResponse, CustomerCloneResponse
from mmm_os.services.clone import (
    clone_connector_config,
    clone_customer_configs,
    clone_feed_template,
    clone_mapping_config,
    clone_rule_set,
    clone_stack,
)

router = APIRouter(prefix="/api/v1", tags=["clone"])

_WRITE_CONFIG = Depends(require_permission(Permission.WRITE_CONFIG))
_ADMIN = Depends(require_permission(Permission.ADMIN))


def _pid(principal: Principal | None) -> uuid.UUID | None:
    return principal.user_id if principal else None


def _clone_and_respond(
    session: Session,
    tenant_id: uuid.UUID,
    principal: Principal | None,
    *,
    entity: str,
    do_clone: Callable[[], object],
) -> CloneResponse:
    clone = do_clone()
    if clone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found")
    record_audit(
        session,
        tenant_id=tenant_id,
        action="clone",
        principal=principal,
        target_type=entity,
        target_id=str(clone.id),  # type: ignore[attr-defined]
        detail={"cloned_from": str(clone.cloned_from)},  # type: ignore[attr-defined]
    )
    session.commit()
    return CloneResponse(
        id=clone.id,  # type: ignore[attr-defined]
        tenant_id=clone.tenant_id,  # type: ignore[attr-defined]
        name=clone.name,  # type: ignore[attr-defined]
        cloned_from=clone.cloned_from,  # type: ignore[attr-defined]
    )


@router.post("/tenants/{tenant_id}/rule-sets/{rid}/clone", response_model=CloneResponse)
def clone_rule_set_route(
    tenant_id: uuid.UUID,
    rid: uuid.UUID,
    body: CloneRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> CloneResponse:
    """Duplicate a rule set (and its rules) into a new draft."""
    return _clone_and_respond(
        session, tenant_id, principal, entity="rule_set",
        do_clone=lambda: clone_rule_set(
            session, tenant_id=tenant_id, rule_set_id=rid,
            target_tenant_id=body.target_tenant_id, new_name=body.new_name,
            created_by=_pid(principal),
        ),
    )


@router.post("/tenants/{tenant_id}/mapping-configs/{mid}/clone", response_model=CloneResponse)
def clone_mapping_config_route(
    tenant_id: uuid.UUID,
    mid: uuid.UUID,
    body: CloneRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> CloneResponse:
    """Duplicate a mapping config (same tenant → next version)."""
    return _clone_and_respond(
        session, tenant_id, principal, entity="mapping_config",
        do_clone=lambda: clone_mapping_config(
            session, tenant_id=tenant_id, mapping_config_id=mid,
            target_tenant_id=body.target_tenant_id, new_name=body.new_name,
            created_by=_pid(principal),
        ),
    )


@router.post("/tenants/{tenant_id}/feed-templates/{fid}/clone", response_model=CloneResponse)
def clone_feed_template_route(
    tenant_id: uuid.UUID,
    fid: uuid.UUID,
    body: CloneRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> CloneResponse:
    """Duplicate a feed template."""
    return _clone_and_respond(
        session, tenant_id, principal, entity="feed_template",
        do_clone=lambda: clone_feed_template(
            session, tenant_id=tenant_id, feed_template_id=fid,
            target_tenant_id=body.target_tenant_id, new_name=body.new_name,
        ),
    )


@router.post("/tenants/{tenant_id}/connector-configs/{cid}/clone", response_model=CloneResponse)
def clone_connector_config_route(
    tenant_id: uuid.UUID,
    cid: uuid.UUID,
    body: CloneRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> CloneResponse:
    """Duplicate a connector config (never its credential/secret, CC-10)."""
    return _clone_and_respond(
        session, tenant_id, principal, entity="connector_config",
        do_clone=lambda: clone_connector_config(
            session, tenant_id=tenant_id, connector_config_id=cid,
            target_tenant_id=body.target_tenant_id, new_name=body.new_name,
        ),
    )


@router.post("/tenants/{tenant_id}/stacks/{sid}/clone", response_model=CloneResponse)
def clone_stack_route(
    tenant_id: uuid.UUID,
    sid: uuid.UUID,
    body: CloneRequest,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> CloneResponse:
    """Duplicate a stack (and its rows) into a new draft."""
    return _clone_and_respond(
        session, tenant_id, principal, entity="stack",
        do_clone=lambda: clone_stack(
            session, tenant_id=tenant_id, stack_id=sid, new_name=body.new_name,
            created_by=_pid(principal),
        ),
    )


@router.post(
    "/tenants/{tenant_id}/clone-configs-to/{target_tenant_id}",
    response_model=CustomerCloneResponse,
)
def clone_customer_route(
    tenant_id: uuid.UUID,
    target_tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
    principal: Principal | None = _ADMIN,
) -> CustomerCloneResponse:
    """Bulk-clone a customer's whole config setup into another customer (admin)."""
    counts = clone_customer_configs(
        session, tenant_id=tenant_id, target_tenant_id=target_tenant_id, created_by=_pid(principal)
    )
    record_audit(
        session,
        tenant_id=tenant_id,
        action="clone.customer",
        principal=principal,
        target_type="tenant",
        target_id=str(target_tenant_id),
        detail=counts,
    )
    session.commit()
    return CustomerCloneResponse(target_tenant_id=target_tenant_id, counts=counts)
