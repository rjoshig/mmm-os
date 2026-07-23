"""Output-generation routes: finalize a sheet into clean, traceable output rows.

Closes the pipeline: after mapping → transform → validation, this persists the
result as ``output_row`` records (CC-3 traceability). Gated on no unresolved
blocking validation flags, and idempotent (re-running replaces prior output).
"""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical, get_storage, require_auth
from mmm_os.auth.service import Principal
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.models import Job, OutputRow
from mmm_os.output import (
    generate_output,
    has_open_blocking_flags,
    list_output_rows,
    prepare_sheet_rows,
)
from mmm_os.schemas.output import (
    ContractField,
    GenerateOutputResponse,
    OutputContract,
    OutputListResponse,
    OutputRowRead,
)
from mmm_os.storage import ObjectStorage

router = APIRouter(prefix="/api/v1", tags=["output"])


@router.post(
    "/tenants/{tenant_id}/jobs/{job_id}/sheets/{sheet_id}/generate-output",
    response_model=GenerateOutputResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_output_route(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    sheet_id: uuid.UUID,
    limit: int = 1000,
    force: bool = False,
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    canonical: CanonicalConfig = Depends(get_canonical),
    principal: Principal | None = Depends(require_auth),
) -> GenerateOutputResponse:
    """Generate clean output for a sheet, applying its saved mapping + rule set.

    Loads the sheet's rows, applies the tenant's saved mapping and the sheet's
    saved rule set, and persists the result as traceable ``output_row`` records.
    Refuses (409) while unresolved blocking-severity validation flags are open,
    unless ``force=true`` is passed (explicit override on the audit record).

    Args:
        tenant_id: The owning tenant.
        job_id: The job the output belongs to.
        sheet_id: The sheet to finalize.
        limit: Maximum number of raw data rows to load.
        force: If true, generate even with open blocking flags (recorded in audit).
        session: Database session (injected).
        storage: Object storage backend (injected).
        canonical: Canonical schema/taxonomies (injected).
        principal: The authenticated actor (recorded in the audit log).

    Returns:
        A summary of the generated output.

    Raises:
        HTTPException: 404 if the job/sheet is not found; 409 if blocked.
    """
    job = session.scalar(tenant_scoped_select(Job, tenant_id).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    if not force and has_open_blocking_flags(session, tenant_id, job_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "output is blocked by unresolved blocking-severity validation flags; "
                "resolve/override them, or re-run with force=true to override"
            ),
        )

    try:
        prepared = prepare_sheet_rows(
            session, storage, canonical, tenant_id=tenant_id, sheet_id=sheet_id, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    written = generate_output(session, tenant_id=tenant_id, job_id=job_id, prepared=prepared)
    record_audit(
        session,
        tenant_id=tenant_id,
        action="output.generate",
        principal=principal,
        target_type="job",
        target_id=str(job_id),
        detail={
            "sheet_id": str(sheet_id),
            "rows_written": written,
            "mapping_version": prepared.mapping_version,
            "rule_set_version": prepared.rule_set_version,
            "forced": force,
        },
    )
    session.commit()
    return GenerateOutputResponse(
        job_id=job_id,
        file_id=prepared.file.id,
        sheet_id=sheet_id,
        rows_written=written,
        mapping_config_version=prepared.mapping_version,
        rule_set_version=prepared.rule_set_version,
    )


@router.get(
    "/tenants/{tenant_id}/jobs/{job_id}/output",
    response_model=OutputListResponse,
)
def get_output_route(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> OutputListResponse:
    """Return the clean output rows generated for a job.

    Args:
        tenant_id: The owning tenant.
        job_id: The job whose output to return.
        limit: Maximum number of rows to return.
        session: Database session (injected).

    Returns:
        The source file and its generated output rows.

    Raises:
        HTTPException: 404 if the job has no generated output.
    """
    file, rows = list_output_rows(session, tenant_id, job_id, limit=limit)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no output generated for this job"
        )
    return OutputListResponse(
        file_id=file.id,
        filename=file.filename,
        rows=[OutputRowRead.model_validate(r) for r in rows],
    )


_TRACE_COLUMNS = ["source_sheet", "source_row", "mapping_config_version", "rule_set_version"]


def _contract_columns(canonical: CanonicalConfig, rows: list[OutputRow]) -> list[ContractField]:
    """Canonical columns present in the output, in schema order (dims, measures, factors)."""
    present: set[str] = set()
    for row in rows:
        present |= set(row.data)
    schema = canonical.schema
    groups = [
        ("dimension", schema.dimensions),
        ("measure", schema.measures),
        ("factor", schema.factors),
    ]
    return [
        ContractField(name=f.name, type=f.type.value, kind=kind)
        for kind, group in groups
        for f in group
        if f.name in present
    ]


@router.get("/tenants/{tenant_id}/jobs/{job_id}/output/contract", response_model=OutputContract)
def output_contract_route(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    sample: int = 5,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> OutputContract:
    """Return the "Export to MMM" contract: the schema + shape a modeler receives.

    The columns (canonical fields present, with type + kind), row count, the config
    versions applied, and a small sample — the handshake before consuming the data.

    Raises:
        HTTPException: 404 if the job has no generated output.
    """
    file, rows = list_output_rows(session, tenant_id, job_id, limit=None)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no output generated for this job"
        )
    first = rows[0] if rows else None
    return OutputContract(
        file_id=file.id,
        filename=file.filename,
        row_count=len(rows),
        columns=_contract_columns(canonical, rows),
        mapping_config_version=first.mapping_config_version if first else None,
        rule_set_version=first.rule_set_version if first else None,
        sample=[r.data for r in rows[:sample]],
    )


@router.get("/tenants/{tenant_id}/jobs/{job_id}/output.csv")
def output_csv_route(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> StreamingResponse:
    """Stream a job's clean output as model-ready CSV (canonical columns + lineage).

    Raises:
        HTTPException: 404 if the job has no generated output.
    """
    file, rows = list_output_rows(session, tenant_id, job_id, limit=None)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no output generated for this job"
        )
    columns = [c.name for c in _contract_columns(canonical, rows)]
    header = columns + _TRACE_COLUMNS

    def _rows() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        for row in rows:
            writer.writerow(
                [row.data.get(c, "") for c in columns]
                + [
                    row.source_sheet,
                    row.source_row,
                    row.mapping_config_version,
                    row.rule_set_version,
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    safe_name = file.filename.rsplit(".", 1)[0]
    return StreamingResponse(
        _rows(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_mmm.csv"'},
    )
