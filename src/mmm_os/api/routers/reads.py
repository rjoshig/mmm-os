"""Read routes for the Review UI (Phase 6): list/detail over files, sheets, jobs.

Thin, tenant-scoped GET endpoints (CC-1). Phases 1–5 exposed only POST/actions;
these reads back the dashboard and mapping screens. No business logic here.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.models import File as FileModel
from mmm_os.models import Job, Profile, Sheet
from mmm_os.models.enums import SheetStatus
from mmm_os.schemas.file import (
    FileDetail,
    FileListItem,
    FileRead,
    JobRead,
    ProfileRead,
    SheetDetail,
    SheetRead,
)

router = APIRouter(prefix="/api/v1", tags=["reads"])


def _latest_job(session: Session, tenant_id: uuid.UUID, file_id: uuid.UUID) -> Job | None:
    """Return a file's most recent job, if any."""
    return session.scalar(
        tenant_scoped_select(Job, tenant_id)
        .where(Job.file_id == file_id)
        .order_by(Job.created_at.desc())
    )


@router.get("/tenants/{tenant_id}/files", response_model=list[FileListItem])
def list_files(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[FileListItem]:
    """List a tenant's files with latest job status + sheet counts (P6-1)."""
    files = session.scalars(
        tenant_scoped_select(FileModel, tenant_id).order_by(FileModel.created_at.desc())
    ).all()
    items: list[FileListItem] = []
    for file in files:
        sheets = session.scalars(
            tenant_scoped_select(Sheet, tenant_id).where(Sheet.file_id == file.id)
        ).all()
        job = _latest_job(session, tenant_id, file.id)
        needs_review = sum(1 for s in sheets if s.status == SheetStatus.NEEDS_REVIEW.value)
        items.append(
            FileListItem(
                file=FileRead.model_validate(file),
                latest_job_status=job.status if job is not None else None,
                sheet_count=len(sheets),
                needs_review_sheets=needs_review,
            )
        )
    return items


@router.get("/tenants/{tenant_id}/files/{file_id}", response_model=FileDetail)
def get_file(
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> FileDetail:
    """Return a file with its sheets and latest job (drill-in)."""
    file = session.scalar(tenant_scoped_select(FileModel, tenant_id).where(FileModel.id == file_id))
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")
    sheets = session.scalars(
        tenant_scoped_select(Sheet, tenant_id)
        .where(Sheet.file_id == file_id)
        .order_by(Sheet.sheet_index)
    ).all()
    job = _latest_job(session, tenant_id, file_id)
    return FileDetail(
        file=FileRead.model_validate(file),
        latest_job=JobRead.model_validate(job) if job is not None else None,
        sheets=[SheetRead.model_validate(s) for s in sheets],
    )


@router.get("/tenants/{tenant_id}/sheets/{sheet_id}", response_model=SheetDetail)
def get_sheet(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> SheetDetail:
    """Return a sheet with its profile (mapping-review input)."""
    sheet = session.scalar(tenant_scoped_select(Sheet, tenant_id).where(Sheet.id == sheet_id))
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sheet not found")
    profile = session.scalar(
        tenant_scoped_select(Profile, tenant_id).where(Profile.sheet_id == sheet_id)
    )
    return SheetDetail(
        sheet=SheetRead.model_validate(sheet),
        profile=ProfileRead.model_validate(profile) if profile is not None else None,
    )


@router.get("/tenants/{tenant_id}/jobs", response_model=list[JobRead])
def list_jobs(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[JobRead]:
    """List a tenant's jobs, most recent first."""
    jobs = session.scalars(
        select(Job).where(Job.tenant_id == tenant_id).order_by(Job.created_at.desc())
    ).all()
    return [JobRead.model_validate(j) for j in jobs]
