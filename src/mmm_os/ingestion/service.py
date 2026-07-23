"""File ingestion service (P1.1-4).

Streams an upload into immutable object storage and creates the tenant-scoped
``file`` + ``job`` records. Parsing/structure detection happen later (01.2).
"""

from __future__ import annotations

import re
import uuid
from typing import IO, Any

from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.ingestion.parsing import iter_sheet_rows
from mmm_os.models import File, Job, Sheet
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


def storage_key_for(file: File) -> str:
    """Return the storage key a file's raw bytes were written to.

    Kept next to :func:`safe_filename` (which derives part of the key) so the
    source layer can locate a stored upload without importing the processing
    module, avoiding an import cycle.
    """
    return f"{file.tenant_id}/{file.id}/{safe_filename(file.filename)}"


def ingest_file(
    session: Session,
    storage: ObjectStorage,
    *,
    tenant_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    stream: IO[bytes],
    max_bytes: int | None = None,
    created_by: uuid.UUID | None = None,
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
        created_by: The user id triggering this ingest (Cycle 6), if known.

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
    job = Job(
        tenant_id=tenant_id,
        file_id=file_id,
        status=JobStatus.PENDING.value,
        created_by=created_by,
    )
    session.add(file)
    session.add(job)
    session.flush()
    return file, job


def load_sheet_rows(
    session: Session,
    storage: ObjectStorage,
    *,
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    limit: int,
) -> tuple[Sheet, list[dict[str, Any]]]:
    """Return a sheet plus its first ``limit`` real data rows, keyed by source column name.

    Streams from the immutable stored file (below the header row). Shared by the
    rows read endpoint and by anything that needs a sheet's raw rows before mapping.

    Args:
        session: The database session.
        storage: The object-storage backend.
        tenant_id: The owning tenant.
        sheet_id: The sheet to read.
        limit: Maximum number of data rows to return.

    Returns:
        The ``Sheet`` and its raw rows (keyed by detected column name).
    """
    sheet = session.scalar(tenant_scoped_select(Sheet, tenant_id).where(Sheet.id == sheet_id))
    if sheet is None:
        raise ValueError("sheet not found")
    file = session.scalar(tenant_scoped_select(File, tenant_id).where(File.id == sheet.file_id))
    if file is None:
        raise ValueError("file not found")

    names = [str(c["name"]) for c in sheet.columns]
    header_index = sheet.header_row_index
    rows: list[dict[str, Any]] = []
    with storage.open(storage_key_for(file)) as stream:
        for i, raw in enumerate(iter_sheet_rows(stream, file.filename, sheet.sheet_index)):
            if header_index is not None and i <= header_index:
                continue
            rows.append({name: (raw[j] if j < len(raw) else None) for j, name in enumerate(names)})
            if len(rows) >= limit:
                break
    return sheet, rows
