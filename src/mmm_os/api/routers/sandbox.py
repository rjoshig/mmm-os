"""Sandbox / test-environment routes (Phase 18)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical, get_storage
from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.session import get_session
from mmm_os.pipeline.sandbox import run_sandbox
from mmm_os.schemas.output import MeasureStatsRead
from mmm_os.schemas.sandbox import SandboxRunResponse
from mmm_os.storage import ObjectStorage

router = APIRouter(prefix="/api/v1", tags=["sandbox"])

_WRITE_CONFIG = Depends(require_permission(Permission.WRITE_CONFIG))


@router.post(
    "/tenants/{tenant_id}/sheets/{sheet_id}/sandbox-run", response_model=SandboxRunResponse
)
def sandbox_run_route(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    sample: int = 20,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    canonical: CanonicalConfig = Depends(get_canonical),
    _: Principal | None = _WRITE_CONFIG,
) -> SandboxRunResponse:
    """Dry-run a sheet through the pipeline without publishing (Phase 18).

    Returns mapping/transform preview, in-memory validation summary, and output
    statistics — **no** ``output_row`` / ``Stack`` is created.
    """
    try:
        result = run_sandbox(
            session, storage, canonical, tenant_id=tenant_id, sheet_id=sheet_id, sample=sample
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    stat_measures = result.stats.measures if result.stats else []
    measures = [MeasureStatsRead(**vars(m)) for m in stat_measures]
    return SandboxRunResponse(
        sheet_id=result.sheet_id,
        row_count=result.row_count,
        sample_rows=[dict(r) for r in result.sample_rows],
        flag_counts=result.flag_counts,
        blocking=result.blocking,
        row_count_stats=result.stats.row_count if result.stats else 0,
        measures=measures,
    )
