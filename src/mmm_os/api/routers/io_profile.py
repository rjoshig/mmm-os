"""Config-driven I/O profile + export-to-destination routes (Phase 14, CC-14)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical, get_storage
from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.output import write_output_to_destination
from mmm_os.schemas.io_profile import (
    ExportToDestinationResponse,
    IoProfileRead,
    IoProfileUpdate,
)
from mmm_os.services.io_profile import resolve_io_profile, update_io_profile
from mmm_os.storage import ObjectStorage

router = APIRouter(prefix="/api/v1", tags=["io-profile"])

_ADMIN = Depends(require_permission(Permission.ADMIN))
_WRITE_CONFIG = Depends(require_permission(Permission.WRITE_CONFIG))


@router.get("/tenants/{tenant_id}/io-profile", response_model=IoProfileRead)
def read_io_profile(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> IoProfileRead:
    """Return the effective (resolved) I/O roots for a tenant (tenant → global → env)."""
    resolved = resolve_io_profile(session, tenant_id)
    return IoProfileRead.model_validate(resolved)


@router.put("/tenants/{tenant_id}/io-profile", response_model=IoProfileRead)
def write_io_profile(
    tenant_id: uuid.UUID,
    body: IoProfileUpdate,
    session: Session = Depends(get_session),
    principal: Principal | None = _ADMIN,
) -> IoProfileRead:
    """Update a tenant's I/O profile (config-as-data, CC-14); returns the resolved roots."""
    update_io_profile(
        session,
        tenant_id,
        input_path=body.input_path,
        output_path=body.output_path,
        temp_path=body.temp_path,
        archive_path=body.archive_path,
        error_path=body.error_path,
        reject_path=body.reject_path,
    )
    resolved = resolve_io_profile(session, tenant_id)
    record_audit(
        session,
        tenant_id=tenant_id,
        action="io_profile.update",
        principal=principal,
        target_type="io_profile",
        target_id=str(tenant_id),
        detail={"output": resolved.output, "archive": resolved.archive},
    )
    session.commit()
    return IoProfileRead.model_validate(resolved)


@router.post(
    "/tenants/{tenant_id}/jobs/{job_id}/export-to-destination",
    response_model=ExportToDestinationResponse,
)
def export_to_destination_route(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    canonical: CanonicalConfig = Depends(get_canonical),
    principal: Principal | None = _WRITE_CONFIG,
) -> ExportToDestinationResponse:
    """Write a job's generated output to the configured ``output`` destination (CC-14).

    Complements the browser CSV download: the same model-ready CSV is written to the
    tenant's configured output path via the storage abstraction.
    """
    from mmm_os.output import list_output_rows

    _, rows = list_output_rows(session, tenant_id, job_id, limit=None)
    key = write_output_to_destination(
        session, storage, canonical, tenant_id=tenant_id, job_id=job_id
    )
    record_audit(
        session,
        tenant_id=tenant_id,
        action="output.export_destination",
        principal=principal,
        target_type="job",
        target_id=str(job_id),
        detail={"written_key": key, "row_count": len(rows)},
    )
    session.commit()
    return ExportToDestinationResponse(
        job_id=str(job_id), written_key=key, row_count=len(rows)
    )
