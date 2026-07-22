"""File ingestion routes (thin — delegates to the ingestion service)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_storage
from mmm_os.core.config import Settings, get_settings
from mmm_os.db.session import get_session
from mmm_os.ingestion.service import ingest_file
from mmm_os.schemas.file import FileRead, IngestResponse, JobRead
from mmm_os.storage import ObjectStorage
from mmm_os.storage.base import FileTooLargeError

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
