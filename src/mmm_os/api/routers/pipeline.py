"""Pipeline route: run the full ingest→map→transform→validate→output chain."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical, get_storage, require_auth
from mmm_os.auth.service import Principal
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.pipeline import run_pipeline
from mmm_os.schemas.pipeline import PipelineRunResponse, SheetPipelineRead
from mmm_os.storage import ObjectStorage

router = APIRouter(prefix="/api/v1", tags=["pipeline"])


@router.post(
    "/tenants/{tenant_id}/files/{file_id}/run-pipeline",
    response_model=PipelineRunResponse,
)
def run_pipeline_route(
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    row_limit: int = 1000,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    canonical: CanonicalConfig = Depends(get_canonical),
    principal: Principal | None = Depends(require_auth),
) -> PipelineRunResponse:
    """Run the full pipeline over a file: map → transform → validate → output.

    Per sheet: resolves (or auto-creates-and-saves) the column mapping by
    signature, applies the saved rule set, validates, and — when not blocked —
    writes clean output. Sheets whose column structure is entirely unknown are
    reported as ``needs_mapping`` (the one-time human step) and skipped. This is
    the single call an external scheduler/cron drives to refresh a source
    end-to-end without a human in the loop.

    Args:
        tenant_id: The owning tenant.
        file_id: The file to run the pipeline on.
        row_limit: Max raw rows loaded per sheet.
        session: Database session (injected).
        storage: Object-storage backend (injected).
        canonical: Canonical schema/taxonomies (injected).
        principal: The authenticated actor (recorded in the audit log).

    Returns:
        A per-sheet summary of the run.

    Raises:
        HTTPException: 404 if the file or its job is not found.
    """
    try:
        result = run_pipeline(
            session, storage, canonical, tenant_id=tenant_id, file_id=file_id, row_limit=row_limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    record_audit(
        session,
        tenant_id=tenant_id,
        action="pipeline.run",
        principal=principal,
        target_type="file",
        target_id=str(file_id),
        detail={"rows_written": result.rows_written, "sheets": len(result.sheets)},
    )
    session.commit()
    return PipelineRunResponse(
        file_id=result.file_id,
        job_id=result.job_id,
        rows_written=result.rows_written,
        sheets=[
            SheetPipelineRead(
                sheet_id=s.sheet_id,
                sheet_name=s.sheet_name,
                needs_mapping=s.needs_mapping,
                mapping_config_version=s.mapping_config_version,
                missing_required=s.missing_required,
                flag_count=s.flag_count,
                blocked=s.blocked,
                output_rows_written=s.output_rows_written,
                rule_set_version=s.rule_set_version,
            )
            for s in result.sheets
        ],
    )
