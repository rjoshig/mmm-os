"""Tenant schema-extension routes (Phase 21, ADR-015)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical
from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.schemas.schema_extension import (
    ResolvedFieldRead,
    ResolvedSchemaResponse,
    SchemaExtensionCreate,
    SchemaExtensionRead,
)
from mmm_os.services.schema_extension import (
    delete_extension,
    list_extensions,
    register_extension,
    resolved_fields,
)

router = APIRouter(prefix="/api/v1", tags=["schema-extensions"])

_WRITE_CONFIG = Depends(require_permission(Permission.WRITE_CONFIG))


@router.get("/tenants/{tenant_id}/schema-extensions", response_model=list[SchemaExtensionRead])
def list_extensions_route(
    tenant_id: uuid.UUID,
    kind: str | None = None,
    session: Session = Depends(get_session),
) -> list[SchemaExtensionRead]:
    """List a tenant's schema extensions (optionally filtered by kind)."""
    return [
        SchemaExtensionRead.model_validate(e)
        for e in list_extensions(session, tenant_id, kind=kind)
    ]


@router.post(
    "/tenants/{tenant_id}/schema-extensions",
    response_model=SchemaExtensionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_extension_route(
    tenant_id: uuid.UUID,
    body: SchemaExtensionCreate,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> SchemaExtensionRead:
    """Register a custom dimension/measure/factor for a tenant (config-as-data)."""
    try:
        ext = register_extension(
            session,
            tenant_id,
            kind=body.kind,
            name=body.name,
            data_type=body.data_type,
            taxonomy_ref=body.taxonomy_ref,
            validation=body.validation,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    record_audit(
        session,
        tenant_id=tenant_id,
        action="schema_extension.register",
        principal=principal,
        target_type="schema_extension",
        target_id=str(ext.id),
        detail={"kind": ext.kind, "name": ext.name},
    )
    session.commit()
    return SchemaExtensionRead.model_validate(ext)


@router.delete(
    "/tenants/{tenant_id}/schema-extensions/{ext_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_extension_route(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> None:
    """Delete a tenant's schema extension."""
    if not delete_extension(session, tenant_id, ext_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="extension not found")
    record_audit(
        session,
        tenant_id=tenant_id,
        action="schema_extension.delete",
        principal=principal,
        target_type="schema_extension",
        target_id=str(ext_id),
        detail={},
    )
    session.commit()


@router.get("/tenants/{tenant_id}/resolved-schema", response_model=ResolvedSchemaResponse)
def resolved_schema_route(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> ResolvedSchemaResponse:
    """Return the resolved schema (canonical core + tenant extensions)."""
    fields = resolved_fields(session, tenant_id, canonical)
    return ResolvedSchemaResponse(
        fields=[ResolvedFieldRead(**vars(f)) for f in fields]
    )
