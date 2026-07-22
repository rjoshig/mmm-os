"""Validation routes: run validation for a job, list flags, and review a flag."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.models import Job
from mmm_os.models.enums import ReviewStatus
from mmm_os.schemas.validation import (
    FlagRead,
    ReviewRequest,
    ValidateRequest,
    ValidateResponse,
)
from mmm_os.validation.policy import Policy
from mmm_os.validation.service import list_flags, review_flag, run_validation

router = APIRouter(prefix="/api/v1", tags=["validation"])

_REVIEW_STATES = {
    ReviewStatus.ACKNOWLEDGED.value,
    ReviewStatus.RESOLVED.value,
    ReviewStatus.OVERRIDDEN.value,
}


@router.post(
    "/tenants/{tenant_id}/jobs/{job_id}/validate",
    response_model=ValidateResponse,
)
def validate_job(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    body: ValidateRequest,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> ValidateResponse:
    """Run validation (+ optional anomaly detection) over records for a job.

    Args:
        tenant_id: The owning tenant.
        job_id: The job the flags attach to.
        body: Records and optional anomaly/policy configuration.
        session: Database session (injected).
        canonical: Canonical schema/taxonomies (injected).

    Returns:
        The persisted flags and whether output is blocked.

    Raises:
        HTTPException: 404 if the job does not exist for this tenant.
    """
    job = session.scalar(tenant_scoped_select(Job, tenant_id).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    flags, blocked = run_validation(
        session,
        tenant_id=tenant_id,
        job_id=job_id,
        table=body.rows,
        schema=canonical.schema,
        policy=Policy(body.policy_overrides),
        anomaly_measure=body.anomaly_measure,
        group_by=body.group_by,
    )
    session.commit()
    return ValidateResponse(blocked=blocked, flags=[FlagRead.model_validate(f) for f in flags])


@router.get(
    "/tenants/{tenant_id}/jobs/{job_id}/validation-flags",
    response_model=list[FlagRead],
)
def get_flags(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[FlagRead]:
    """List a job's validation flags."""
    return [FlagRead.model_validate(f) for f in list_flags(session, tenant_id, job_id)]


@router.post(
    "/tenants/{tenant_id}/validation-flags/{flag_id}/review",
    response_model=FlagRead,
)
def review(
    tenant_id: uuid.UUID,
    flag_id: uuid.UUID,
    body: ReviewRequest,
    session: Session = Depends(get_session),
) -> FlagRead:
    """Record a review decision (acknowledge/resolve/override) on a flag (P4-5).

    Args:
        tenant_id: The owning tenant.
        flag_id: The flag to review.
        body: The review decision.
        session: Database session (injected).

    Returns:
        The updated flag.

    Raises:
        HTTPException: 400 for an invalid status; 404 if the flag is not found.
    """
    if body.status not in _REVIEW_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid status: {body.status!r}"
        )
    flag = review_flag(
        session,
        tenant_id=tenant_id,
        flag_id=flag_id,
        status=body.status,
        resolved_by=body.resolved_by,
    )
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="flag not found")
    session.commit()
    return FlagRead.model_validate(flag)
