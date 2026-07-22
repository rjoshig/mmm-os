"""Ingestion processing: structure detection over a stored file (P1-2..P1-4, P1-7).

Routes the stored file through the source-agnostic :class:`~mmm_os.sources.FileSource`
(CC-9): a file is simply the first kind of ``SourceConnector``. The returned
:class:`~mmm_os.sources.LandedDataset` — one landed table per non-empty sheet,
with detected header + column structure — is persisted as ``sheet`` records and
then profiled, all under a ``job`` whose status and per-stage events are recorded
(CC-7). Malformed files mark the job failed with a readable reason rather than
crashing (P1-7).
"""

from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.ingestion.parsing import iter_sheet_rows
from mmm_os.ingestion.profiling import profile_rows
from mmm_os.ingestion.service import storage_key_for
from mmm_os.models import File, Job, Profile, Sheet
from mmm_os.models.enums import JobStatus, SheetStatus
from mmm_os.models.mixins import utcnow
from mmm_os.sources import FetchRequest, FileSource
from mmm_os.storage.base import ObjectStorage


def _latest_job(session: Session, file: File) -> Job:
    """Return the file's most recent job, creating one if none exists."""
    job = session.scalar(
        select(Job)
        .where(Job.file_id == file.id, Job.tenant_id == file.tenant_id)
        .order_by(Job.created_at.desc())
    )
    if job is None:
        job = Job(tenant_id=file.tenant_id, file_id=file.id, status=JobStatus.PENDING.value)
        session.add(job)
        session.flush()
    return job


def process_file(
    session: Session,
    storage: ObjectStorage,
    file: File,
    *,
    preview_rows: int,
    distinct_limit: int = 1000,
    sample_limit: int = 20,
) -> tuple[Job, list[Sheet]]:
    """Detect structure for a stored file, persist its sheets, and profile them.

    Args:
        session: The database session.
        storage: The object-storage backend.
        file: The file to process.
        preview_rows: Rows to preview per sheet for detection.
        distinct_limit: Cap on distinct values tracked per column when profiling.
        sample_limit: Cap on sample values kept per column when profiling.

    Returns:
        The processed ``(job, sheets)``. On a parse failure the job is marked
        failed (no exception propagates).
    """
    job = _latest_job(session, file)
    job.status = JobStatus.RUNNING.value
    job.started_at = utcnow()
    session.flush()

    started = time.monotonic()
    sheets: list[Sheet] = []
    try:
        dataset = FileSource(storage).fetch(
            FetchRequest(
                ref={
                    "file_id": str(file.id),
                    "storage_key": storage_key_for(file),
                    "filename": file.filename,
                },
                options={"preview_rows": preview_rows},
            )
        )

        for table in dataset.tables:
            status = SheetStatus.PARSED.value if table.confident else SheetStatus.NEEDS_REVIEW.value
            sheet = Sheet(
                tenant_id=file.tenant_id,
                file_id=file.id,
                sheet_name=table.name,
                sheet_index=table.index,
                header_row_index=table.header_row_index,
                status=status,
                columns=table.columns,
            )
            session.add(sheet)
            sheets.append(sheet)
        session.flush()

        for sheet in sheets:
            _profile_sheet(
                session,
                storage,
                file,
                sheet,
                distinct_limit=distinct_limit,
                sample_limit=sample_limit,
            )

        _finish_job(session, job, JobStatus.SUCCEEDED, started, f"{len(sheets)} sheet(s)")
    except Exception as exc:  # noqa: BLE001 - malformed files must not crash (P1-7)
        sheets = []
        _finish_job(session, job, JobStatus.FAILED, started, str(exc), error=str(exc))

    return job, sheets


def _profile_sheet(
    session: Session,
    storage: ObjectStorage,
    file: File,
    sheet: Sheet,
    *,
    distinct_limit: int,
    sample_limit: int,
) -> Profile:
    """Stream a sheet's rows, compute per-column stats, and persist a profile."""
    with storage.open(storage_key_for(file)) as stream:
        rows = iter_sheet_rows(stream, file.filename, sheet.sheet_index)
        row_count, column_stats = profile_rows(
            rows,
            sheet.columns,
            sheet.header_row_index,
            distinct_limit=distinct_limit,
            sample_limit=sample_limit,
        )
    profile = Profile(
        tenant_id=file.tenant_id,
        sheet_id=sheet.id,
        row_count=row_count,
        column_stats={"columns": column_stats},
    )
    session.add(profile)
    session.flush()
    return profile


def _finish_job(
    session: Session,
    job: Job,
    status: JobStatus,
    started: float,
    message: str,
    *,
    error: str | None = None,
) -> None:
    """Set the job's terminal status and record a structure-detection event."""
    from mmm_os.models import JobEvent

    job.status = status.value
    job.finished_at = utcnow()
    job.error = error
    session.add(
        JobEvent(
            tenant_id=job.tenant_id,
            job_id=job.id,
            stage="structure_detection",
            status=status.value,
            message=message,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    )
    session.flush()
