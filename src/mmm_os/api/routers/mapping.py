"""Mapping routes: save a sheet's mapping and auto-map by signature (02.2)."""

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
from mmm_os.mapping.engine import MappingResult, apply_mapping
from mmm_os.mapping.service import auto_map_sheet, save_sheet_mapping
from mmm_os.models import Sheet
from mmm_os.schemas.mapping import (
    AutoMapResponse,
    MappedColumnRead,
    MappingConfigRead,
    MappingValidation,
    SaveMappingRequest,
    SaveMappingResponse,
)

router = APIRouter(prefix="/api/v1", tags=["mapping"])


def _to_validation(result: MappingResult) -> MappingValidation:
    """Convert an engine ``MappingResult`` into the API validation schema."""
    return MappingValidation(
        mapped=[
            MappedColumnRead(source_name=m.source_name, canonical_field=m.canonical_field)
            for m in result.mapped
        ],
        ignored=result.ignored,
        invalid=result.invalid,
        missing_required=result.missing_required,
        is_complete=result.is_complete,
    )


def _get_sheet(session: Session, tenant_id: uuid.UUID, sheet_id: uuid.UUID) -> Sheet:
    sheet = session.scalar(tenant_scoped_select(Sheet, tenant_id).where(Sheet.id == sheet_id))
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sheet not found")
    return sheet


@router.post(
    "/tenants/{tenant_id}/sheets/{sheet_id}/mapping",
    status_code=status.HTTP_201_CREATED,
    response_model=SaveMappingResponse,
)
def save_mapping(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    body: SaveMappingRequest,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
    principal: Principal | None = Depends(require_auth),
) -> SaveMappingResponse:
    """Save (version) a mapping for a sheet and return its validation.

    Args:
        tenant_id: The owning tenant.
        sheet_id: The sheet whose signature keys the config.
        body: The mapping payload.
        session: Database session (injected).
        canonical: Canonical schema/taxonomies (injected).
        principal: The authenticated actor (recorded in the audit log).

    Returns:
        The saved config and the validation of applying it to the sheet.
    """
    sheet = _get_sheet(session, tenant_id, sheet_id)
    config = save_sheet_mapping(
        session,
        tenant_id=tenant_id,
        sheet=sheet,
        name=body.name,
        mapping=body.mapping,
        layer=body.layer,
    )
    result = apply_mapping(sheet.columns, body.mapping, canonical.schema)
    record_audit(
        session,
        tenant_id=tenant_id,
        action="mapping.save",
        principal=principal,
        target_type="sheet",
        target_id=str(sheet_id),
        detail={"config_version": config.version},
    )
    session.commit()
    return SaveMappingResponse(
        config=MappingConfigRead.model_validate(config),
        validation=_to_validation(result),
    )


@router.post(
    "/tenants/{tenant_id}/sheets/{sheet_id}/automap",
    response_model=AutoMapResponse,
)
def automap(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> AutoMapResponse:
    """Auto-apply a saved config to a sheet by column signature (P2-3).

    Args:
        tenant_id: The owning tenant.
        sheet_id: The sheet to map.
        session: Database session (injected).
        canonical: Canonical schema/taxonomies (injected).

    Returns:
        The matched mapping + validation, or ``matched=False`` (needs mapping).
    """
    sheet = _get_sheet(session, tenant_id, sheet_id)
    auto = auto_map_sheet(session, tenant_id, sheet, canonical.schema)
    return AutoMapResponse(
        signature=auto.signature,
        matched=auto.matched,
        mapping=auto.mapping,
        validation=_to_validation(auto.result) if auto.result is not None else None,
    )
