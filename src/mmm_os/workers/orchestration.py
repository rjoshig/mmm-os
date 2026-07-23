"""Batch orchestration: fan a set of files out into per-file tasks (Phase 7).

Turns a batch (e.g. 50–60 files) into individual, tenant-bound tasks on the queue
(P7-2), skipping files already processed successfully so re-running a batch does
not duplicate output (idempotent, CC-6). Each task reuses the Phase-1
``process_file`` under its own job, so per-file status + the job-event timeline
(CC-7) come for free.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.ingestion.process import process_file
from mmm_os.models import File, Job
from mmm_os.models.enums import JobStatus
from mmm_os.observability import (
    BATCH_QUEUE_DEPTH,
    JOBS_DEAD_LETTERED,
    JOBS_PROCESSED,
    JOBS_RETRIED,
    registry,
)
from mmm_os.storage.base import ObjectStorage
from mmm_os.workers.queue import DrainResult, Task, TaskQueue


def _latest_job(session: Session, file: File) -> Job | None:
    """Return a file's most recent job, if any."""
    return session.scalar(
        select(Job)
        .where(Job.file_id == file.id, Job.tenant_id == file.tenant_id)
        .order_by(Job.created_at.desc())
    )


def already_succeeded(session: Session, file: File) -> bool:
    """Return whether the file's latest job already succeeded (idempotency, CC-6)."""
    latest = _latest_job(session, file)
    return latest is not None and latest.status == JobStatus.SUCCEEDED.value


def enqueue_batch(
    queue: TaskQueue,
    session: Session,
    storage: ObjectStorage,
    files: list[File],
    *,
    preview_rows: int = 1000,
    distinct_limit: int = 1000,
    sample_limit: int = 20,
    max_retries: int = 2,
) -> int:
    """Enqueue per-file processing tasks for a batch; return how many were enqueued.

    Files whose latest job already succeeded are skipped (idempotent re-runs).
    """
    enqueued = 0
    for file in files:
        if already_succeeded(session, file):
            continue

        def _run(target: File = file) -> None:
            process_file(
                session,
                storage,
                target,
                preview_rows=preview_rows,
                distinct_limit=distinct_limit,
                sample_limit=sample_limit,
            )

        queue.enqueue(
            Task(
                tenant_id=file.tenant_id,
                run=_run,
                name=f"process:{file.id}",
                max_retries=max_retries,
            )
        )
        enqueued += 1
    return enqueued


def process_batch(
    queue: TaskQueue,
    session: Session,
    storage: ObjectStorage,
    files: list[File],
    **kwargs: int,
) -> DrainResult:
    """Enqueue a batch and drain the queue, recording metrics (CC-7)."""
    enqueued = enqueue_batch(queue, session, storage, files, **kwargs)
    registry.observe(BATCH_QUEUE_DEPTH, float(enqueued))
    result = queue.drain()
    registry.increment(JOBS_PROCESSED, float(result.processed))
    registry.increment(JOBS_RETRIED, float(result.retried))
    registry.increment(JOBS_DEAD_LETTERED, float(len(result.dead_letters)))
    return result
