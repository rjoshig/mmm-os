"""File ingestion service (P1.1-4).

Streams an upload into immutable object storage and creates the tenant-scoped
``file`` + ``job`` records. Parsing/structure detection happen later (01.2).
"""

from __future__ import annotations

import re
import uuid
from typing import IO

from sqlalchemy.orm import Session

from mmm_os.models import File, Job
from mmm_os.models.enums import JobStatus
from mmm_os.storage.base import ObjectStorage

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(filename: str) -> str:
    """Reduce an uploaded filename to a safe basename.

    Args:
        filename: The client-supplied filename.

    Returns:
        A sanitised basename (path components stripped), or ``"upload"`` if empty.
    """
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _UNSAFE.sub("_", base).strip("._")
    return cleaned or "upload"


def ingest_file(
    session: Session,
    storage: ObjectStorage,
    *,
    tenant_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    stream: IO[bytes],
    max_bytes: int | None = None,
) -> tuple[File, Job]:
    """Store a raw upload immutably and create its file + job records.

    Args:
        session: The database session.
        storage: The object-storage backend.
        tenant_id: The owning tenant.
        filename: The uploaded filename.
        content_type: The uploaded content type, if known.
        stream: A readable binary stream of the upload's bytes.
        max_bytes: Optional size ceiling (raises ``FileTooLargeError`` if exceeded).

    Returns:
        The created ``(File, Job)`` pair, flushed.
    """
    file_id = uuid.uuid4()
    key = f"{tenant_id}/{file_id}/{safe_filename(filename)}"
    stored = storage.put(key, stream, max_bytes=max_bytes)

    file = File(
        id=file_id,
        tenant_id=tenant_id,
        filename=filename,
        content_type=content_type,
        byte_size=stored.size,
        storage_uri=stored.uri,
        checksum_sha256=stored.checksum_sha256,
    )
    job = Job(tenant_id=tenant_id, file_id=file_id, status=JobStatus.PENDING.value)
    session.add(file)
    session.add(job)
    session.flush()
    return file, job
