"""Write generated output to a configured destination + record the file lifecycle.

Phase 14 (CC-14): besides the browser CSV download, generated output is written to
the tenant's configured ``output`` path (via the ``ObjectStorage`` abstraction,
never a hardcoded host), and the processed file's lifecycle (archive on success,
error/reject on failure) is recorded on the job timeline (CC-3/CC-7).

The immutable raw copy (CC-2) is untouched — the output artifact is derived data
and the lifecycle records the logical destination for the processed file.
"""

from __future__ import annotations

import csv
import io
import uuid

from sqlalchemy.orm import Session

from mmm_os.canonical import CanonicalConfig
from mmm_os.core.config import Settings, get_settings
from mmm_os.models import JobEvent, OutputRow
from mmm_os.output.service import list_output_rows
from mmm_os.services.io_profile import ResolvedIoProfile, resolve_io_profile
from mmm_os.storage.base import ObjectStorage

_TRACE_COLUMNS = ["source_sheet", "source_row", "mapping_config_version", "rule_set_version"]


def canonical_output_columns(canonical: CanonicalConfig, rows: list[OutputRow]) -> list[str]:
    """Canonical field names present in ``rows``, in schema order (dims, measures, factors)."""
    present: set[str] = set()
    for row in rows:
        present |= set(row.data)
    schema = canonical.schema
    ordered: list[str] = []
    for group in (schema.dimensions, schema.measures, schema.factors):
        ordered += [f.name for f in group if f.name in present]
    return ordered


def render_output_csv(canonical: CanonicalConfig, rows: list[OutputRow]) -> bytes:
    """Render output rows to model-ready CSV bytes (canonical columns + lineage)."""
    columns = canonical_output_columns(canonical, rows)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns + _TRACE_COLUMNS)
    for row in rows:
        writer.writerow(
            [row.data.get(c, "") for c in columns]
            + [row.source_sheet, row.source_row, row.mapping_config_version, row.rule_set_version]
        )
    return buffer.getvalue().encode("utf-8")


def _record_event(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    stage: str,
    status: str,
    message: str,
) -> None:
    session.add(
        JobEvent(
            tenant_id=tenant_id,
            job_id=job_id,
            stage=stage,
            status=status,
            message=message,
        )
    )


def write_output_to_destination(
    session: Session,
    storage: ObjectStorage,
    canonical: CanonicalConfig,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    settings: Settings | None = None,
) -> str | None:
    """Write a job's generated output as CSV to the configured ``output`` destination.

    Returns the storage key written, or ``None`` if the job has no output. The
    output artifact is derived data (not the immutable raw file, CC-2), so a
    re-generation overwrites it (delete-then-put). Records a ``JobEvent`` (CC-7).
    """
    settings = settings or get_settings()
    file, rows = list_output_rows(session, tenant_id, job_id, limit=None)
    if file is None or not rows:
        return None
    resolved = resolve_io_profile(session, tenant_id, settings)
    key = f"{resolved.output}/tenant/{tenant_id}/job/{job_id}.csv"
    payload = render_output_csv(canonical, rows)
    # Derived artifact: overwritable (immutability is for raw files only, CC-2).
    storage.delete(key)
    storage.put(key, io.BytesIO(payload))
    _record_event(
        session,
        tenant_id=tenant_id,
        job_id=job_id,
        stage="output.destination",
        status="written",
        message=f"wrote {len(rows)} rows to {key}",
    )
    session.flush()
    return key


def record_file_lifecycle(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    file_id: uuid.UUID,
    outcome: str,
    resolved: ResolvedIoProfile | None = None,
    settings: Settings | None = None,
) -> str:
    """Record where a processed file goes in its lifecycle (archive/error/reject).

    ``outcome`` is one of ``archive`` (success), ``error`` (job failure), or
    ``reject`` (validation-rejected). Returns the computed destination prefix/key
    and writes a ``JobEvent`` for traceability (CC-3/CC-7). Physical relocation of
    raw bytes is a storage-backend concern (OQ-14.2); the raw original stays
    immutable (CC-2).
    """
    if outcome not in {"archive", "error", "reject"}:
        raise ValueError(f"unknown lifecycle outcome {outcome!r}")
    settings = settings or get_settings()
    resolved = resolved or resolve_io_profile(session, tenant_id, settings)
    prefix = resolved.prefix(outcome)
    key = f"{prefix}/tenant/{tenant_id}/file/{file_id}"
    _record_event(
        session,
        tenant_id=tenant_id,
        job_id=job_id,
        stage="file.lifecycle",
        status=outcome,
        message=f"file {file_id} routed to {key}",
    )
    session.flush()
    return key
