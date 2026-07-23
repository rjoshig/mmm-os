"""File ingestion routes (thin — delegates to the ingestion service)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_storage
from mmm_os.core.config import Settings, get_settings
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.ingestion.process import process_file
from mmm_os.ingestion.service import ingest_file
from mmm_os.models import File as FileModel
from mmm_os.schemas.file import (
    BatchResponse,
    FileRead,
    IngestResponse,
    JobRead,
    ProcessResponse,
    SheetRead,
)
from mmm_os.storage import ObjectStorage
from mmm_os.storage.base import FileTooLargeError
from mmm_os.workers import EagerTaskQueue, process_batch

router = APIRouter(prefix="/api/v1", tags=["files"])


@router.post(
    "/tenants/{tenant_id}/files",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestResponse,
)
def upload_file(
    tenant_id: uuid.UUID,
    upload: UploadFile = File(...),
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """Ingest an uploaded file: store it immutably and create file + job records.

    Args:
        tenant_id: The owning tenant.
        upload: The uploaded file.
        session: Database session (injected).
        storage: Object-storage backend (injected).
        settings: Application settings (injected).

    Returns:
        The created file and job.

    Raises:
        HTTPException: 413 if the upload exceeds the configured size ceiling.
    """
    try:
        file, job = ingest_file(
            session,
            storage,
            tenant_id=tenant_id,
            filename=upload.filename or "upload",
            content_type=upload.content_type,
            stream=upload.file,
            max_bytes=settings.max_upload_bytes,
        )
    except FileTooLargeError as exc:
        # 413 Content Too Large (constant name varies across Starlette versions).
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    session.commit()
    return IngestResponse(file=FileRead.model_validate(file), job=JobRead.model_validate(job))


@router.post(
    "/tenants/{tenant_id}/files/{file_id}/process",
    response_model=ProcessResponse,
)
def process_file_route(
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> ProcessResponse:
    """Run structure detection over a stored file and persist its sheets.

    Args:
        tenant_id: The owning tenant.
        file_id: The file to process.
        session: Database session (injected).
        storage: Object-storage backend (injected).
        settings: Application settings (injected).

    Returns:
        The job (succeeded/failed) and the detected sheets.

    Raises:
        HTTPException: 404 if the file does not exist for this tenant.
    """
    file = session.scalar(tenant_scoped_select(FileModel, tenant_id).where(FileModel.id == file_id))
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    job, sheets = process_file(
        session,
        storage,
        file,
        preview_rows=settings.structure_preview_rows,
        distinct_limit=settings.profile_distinct_limit,
        sample_limit=settings.profile_sample_limit,
    )
    session.commit()
    return ProcessResponse(
        job=JobRead.model_validate(job),
        sheets=[SheetRead.model_validate(s) for s in sheets],
    )


@router.post("/tenants/{tenant_id}/batches/process", response_model=BatchResponse)
def process_all_files(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> BatchResponse:
    """Fan the tenant's files out onto the task queue and drain it (P7-1/P7-2).

    Runs through the source-agnostic ``TaskQueue`` (``EagerTaskQueue`` in dev,
    Celery+Redis in prod, ADR-007): per-tenant fair, idempotent (already-succeeded
    files are skipped, CC-6), with bounded retries + dead-lettering.
    """
    files = list(session.scalars(tenant_scoped_select(FileModel, tenant_id)).all())
    queue = EagerTaskQueue()
    result = process_batch(
        queue,
        session,
        storage,
        files,
        preview_rows=settings.structure_preview_rows,
        distinct_limit=settings.profile_distinct_limit,
        sample_limit=settings.profile_sample_limit,
    )
    session.commit()
    return BatchResponse(
        enqueued=result.processed + len(result.dead_letters),
        processed=result.processed,
        retried=result.retried,
        dead_lettered=len(result.dead_letters),
    )
