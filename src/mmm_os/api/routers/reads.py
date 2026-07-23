"""Read routes for the Review UI (Phase 6): list/detail over files, sheets, jobs.

Thin, tenant-scoped GET endpoints (CC-1). Phases 1–5 exposed only POST/actions;
these reads back the dashboard and mapping screens. No business logic here.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical, get_storage
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.ingestion.service import load_sheet_rows
from mmm_os.mapping.service import resolve_mapping
from mmm_os.mapping.signature import column_signature
from mmm_os.models import File as FileModel
from mmm_os.models import Job, JobEvent, OutputRow, Profile, Sheet, ValidationFlag
from mmm_os.models.enums import ReviewStatus, Severity, SheetStatus
from mmm_os.schemas.canonical import CanonicalFieldRead, CanonicalFieldsResponse
from mmm_os.schemas.file import (
    FileDetail,
    FileListItem,
    FileRead,
    JobDetail,
    JobEventRead,
    JobRead,
    ProfileRead,
    SheetDetail,
    SheetRead,
    SheetRowsResponse,
)
from mmm_os.schemas.pipeline import FilePipelineStatus, SheetPipelineStatus
from mmm_os.storage import ObjectStorage
from mmm_os.transform.service import get_rule_set, rule_set_name_for_sheet

router = APIRouter(prefix="/api/v1", tags=["reads"])


@router.get("/canonical/fields", response_model=CanonicalFieldsResponse)
def canonical_fields(
    canonical: CanonicalConfig = Depends(get_canonical),
) -> CanonicalFieldsResponse:
    """List the canonical fields a source column may map to (mapping UI)."""
    schema = canonical.schema
    fields = [
        CanonicalFieldRead(
            name=f.name,
            type=f.type.value,
            required=f.required,
            kind="dimension",
            taxonomy=f.taxonomy,
        )
        for f in schema.dimensions
    ] + [
        CanonicalFieldRead(
            name=f.name, type=f.type.value, required=f.required, kind="measure", taxonomy=f.taxonomy
        )
        for f in schema.measures
    ] + [
        CanonicalFieldRead(
            name=f.name, type=f.type.value, required=f.required, kind="factor", taxonomy=f.taxonomy
        )
        for f in schema.factors
    ]
    return CanonicalFieldsResponse(
        version=schema.version,
        fields=fields,
        min_measures_required=schema.measure_policy.min_required,
    )


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


@router.get("/tenants/{tenant_id}/sheets/{sheet_id}/rows", response_model=SheetRowsResponse)
def get_sheet_rows(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    limit: int = 20,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
) -> SheetRowsResponse:
    """Return the first ``limit`` real data rows of a sheet (below the header).

    Streams from the immutable stored file and keys each row by the sheet's
    detected column names. Used by the transform-preview and validation screens
    instead of zipped profile samples.
    """
    try:
        sheet, rows = load_sheet_rows(
            session, storage, tenant_id=tenant_id, sheet_id=sheet_id, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    names = [str(c["name"]) for c in sheet.columns]
    return SheetRowsResponse(columns=names, rows=rows)


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


@router.get("/tenants/{tenant_id}/jobs/{job_id}", response_model=JobDetail)
def get_job(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> JobDetail:
    """Return a job with its filename and ordered stage events (Runs drill-in, CC-7)."""
    job = session.scalar(tenant_scoped_select(Job, tenant_id).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    filename: str | None = None
    if job.file_id is not None:
        file = session.scalar(
            tenant_scoped_select(FileModel, tenant_id).where(FileModel.id == job.file_id)
        )
        filename = file.filename if file is not None else None
    events = session.scalars(
        select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.created_at)
    ).all()
    return JobDetail(
        job=JobRead.model_validate(job),
        filename=filename,
        events=[JobEventRead.model_validate(e) for e in events],
    )


# Stage states for the file-detail pipeline stepper (Phase 6 UX overhaul).
_RESOLVED_REVIEW = {ReviewStatus.RESOLVED.value, ReviewStatus.OVERRIDDEN.value}


@router.get(
    "/tenants/{tenant_id}/files/{file_id}/pipeline-status",
    response_model=FilePipelineStatus,
)
def get_pipeline_status(
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> FilePipelineStatus:
    """Return the per-sheet + file-level pipeline stage for the UI stepper.

    Per sheet: whether a saved mapping resolves for its column signature and
    whether a saved rule set exists. File-level: whether validation has run
    (flags exist), how many blocking flags are still open, and whether any clean
    output rows exist.
    """
    file = session.scalar(
        tenant_scoped_select(FileModel, tenant_id).where(FileModel.id == file_id)
    )
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    sheets = session.scalars(
        select(Sheet)
        .where(Sheet.tenant_id == tenant_id, Sheet.file_id == file.id)
        .order_by(Sheet.sheet_index)
    ).all()

    sheet_status: list[SheetPipelineStatus] = []
    for sheet in sheets:
        mapping = resolve_mapping(session, tenant_id, column_signature(sheet.columns))
        rule_set = get_rule_set(session, tenant_id, rule_set_name_for_sheet(sheet))
        sheet_status.append(
            SheetPipelineStatus(
                sheet_id=sheet.id,
                sheet_name=sheet.sheet_name,
                has_mapping=bool(mapping),
                has_rule_set=rule_set is not None,
            )
        )

    job = session.scalar(
        select(Job)
        .where(Job.tenant_id == tenant_id, Job.file_id == file.id)
        .order_by(Job.created_at.desc())
    )
    flags = (
        session.scalars(
            select(ValidationFlag).where(
                ValidationFlag.tenant_id == tenant_id, ValidationFlag.job_id == job.id
            )
        ).all()
        if job is not None
        else []
    )
    blocking_open = sum(
        1
        for f in flags
        if f.severity == Severity.BLOCKING.value and f.review_status not in _RESOLVED_REVIEW
    )
    has_output = (
        session.scalar(
            select(OutputRow.id)
            .where(OutputRow.tenant_id == tenant_id, OutputRow.source_file_id == file.id)
            .limit(1)
        )
        is not None
    )

    return FilePipelineStatus(
        file_id=file.id,
        validated=bool(flags),
        blocking_open=blocking_open,
        has_output=has_output,
        sheets=sheet_status,
    )
