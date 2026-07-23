"""Output-generation service: prepare rows + persist canonical output (CC-3).

Reusable row preparation (load → map → transform) shared with the validation
sheet endpoint, plus the persistence of clean ``OutputRow`` records gated on
unresolved blocking validation flags. Re-running a job replaces its prior output
(idempotent, CC-6).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from mmm_os.canonical import CanonicalConfig
from mmm_os.ingestion.service import load_sheet_rows
from mmm_os.mapping.engine import map_rows
from mmm_os.mapping.service import resolve_mapping
from mmm_os.mapping.signature import column_signature
from mmm_os.models import File, MappingConfig, OutputRow, Sheet, ValidationFlag
from mmm_os.models.enums import ReviewStatus, RuleLayer, Severity
from mmm_os.services.tenant_settings import reporting_context
from mmm_os.storage.base import ObjectStorage
from mmm_os.transform.engine import apply_rules
from mmm_os.transform.registry import RuleContext
from mmm_os.transform.service import get_rule_set, resolve_rule_specs, rule_set_name_for_sheet

# A blocking flag only clears output once it is resolved or overridden —
# "acknowledged" means "seen, not fixed" and still blocks (matches the UI gate).
_RESOLVED_STATES = {ReviewStatus.RESOLVED.value, ReviewStatus.OVERRIDDEN.value}


@dataclass(frozen=True)
class PreparedRows:
    """A sheet's rows fully prepared for output/validation.

    Attributes:
        sheet: The source sheet.
        file: The source file (for traceability).
        rows: Raw → mapped → transformed canonical rows.
        mapping_version: The customer-layer mapping-config version applied (if any).
        rule_set_version: The saved rule-set version applied (if any).
    """

    sheet: Sheet
    file: File
    rows: list[dict[str, object]]
    mapping_version: int | None
    rule_set_version: int | None


def prepare_sheet_rows(
    session: Session,
    storage: ObjectStorage,
    canonical: CanonicalConfig,
    *,
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    limit: int = 1000,
) -> PreparedRows:
    """Load a sheet's raw rows and apply its saved mapping + rule set.

    Mirrors the validation sheet endpoint's preparation so validation and output
    operate on identical data.
    """
    sheet, raw_rows = load_sheet_rows(
        session, storage, tenant_id=tenant_id, sheet_id=sheet_id, limit=limit
    )
    file = session.scalar(select(File).where(File.id == sheet.file_id))
    if file is None:  # pragma: no cover - load_sheet_rows already validates the file
        raise ValueError("file not found")

    signature = column_signature(sheet.columns)
    mapping = resolve_mapping(session, tenant_id, signature)
    mapped_rows = map_rows(raw_rows, mapping)

    rule_name = rule_set_name_for_sheet(sheet)
    rule_specs = resolve_rule_specs(session, tenant_id, rule_name)
    transformed_rows = apply_rules(
        mapped_rows,
        rule_specs,
        RuleContext(
            taxonomies=canonical.taxonomies,
            schema=canonical.schema,
            reporting=reporting_context(session, tenant_id),
        ),
    )

    return PreparedRows(
        sheet=sheet,
        file=file,
        rows=transformed_rows,
        mapping_version=_latest_mapping_version(session, tenant_id, signature),
        rule_set_version=_latest_rule_set_version(session, tenant_id, rule_name),
    )


def _latest_mapping_version(
    session: Session, tenant_id: uuid.UUID, signature: str
) -> int | None:
    """Return the latest active customer-layer mapping-config version (if any)."""
    return session.scalar(
        select(func.max(MappingConfig.version)).where(
            MappingConfig.tenant_id == tenant_id,
            MappingConfig.file_signature == signature,
            MappingConfig.layer == RuleLayer.CUSTOMER.value,
            MappingConfig.is_active.is_(True),
        )
    )


def _latest_rule_set_version(
    session: Session, tenant_id: uuid.UUID, name: str
) -> int | None:
    """Return the latest saved rule-set version for a name (if any)."""
    rule_set = get_rule_set(session, tenant_id, name)
    return rule_set.version if rule_set is not None else None


def has_open_blocking_flags(session: Session, tenant_id: uuid.UUID, job_id: uuid.UUID) -> bool:
    """Return whether a job has any unresolved blocking-severity validation flags.

    A blocking flag is resolved only once a human sets it to ``resolved`` or
    ``overridden``; ``acknowledged`` ("seen, not fixed") still blocks output.
    """
    flags = session.scalars(
        select(ValidationFlag).where(
            ValidationFlag.tenant_id == tenant_id, ValidationFlag.job_id == job_id
        )
    ).all()
    return any(
        f.severity == Severity.BLOCKING.value and f.review_status not in _RESOLVED_STATES
        for f in flags
    )


def generate_output(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    prepared: PreparedRows,
) -> int:
    """Persist clean output rows for a job (idempotently replacing any prior output).

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        job_id: The job this output belongs to.
        prepared: The sheet's prepared (mapped + transformed) rows.

    Returns:
        The number of output rows written.
    """
    # Idempotent (CC-6): re-generating a job replaces its prior output rows.
    session.execute(
        delete(OutputRow).where(
            OutputRow.tenant_id == tenant_id,
            OutputRow.source_file_id == prepared.file.id,
            OutputRow.source_sheet == (prepared.sheet.sheet_name or f"sheet-{prepared.sheet.id}"),
        )
    )

    sheet_label = prepared.sheet.sheet_name or f"sheet-{prepared.sheet.id}"
    for index, row in enumerate(prepared.rows):
        session.add(
            OutputRow(
                tenant_id=tenant_id,
                source_file_id=prepared.file.id,
                source_sheet=sheet_label,
                source_row=index,
                mapping_config_version=prepared.mapping_version,
                rule_set_version=prepared.rule_set_version,
                ingested_at=prepared.file.created_at,
                data=dict(row),
            )
        )
    session.flush()
    return len(prepared.rows)


def list_output_rows(
    session: Session, tenant_id: uuid.UUID, job_id: uuid.UUID, limit: int | None = 100
) -> tuple[File | None, list[OutputRow]]:
    """Return the source file and the clean output rows for a job.

    Output rows are keyed by source file (not job) so they survive job re-runs;
    we resolve the file via the job, then return its latest output rows. ``limit``
    of ``None`` returns every row (used by CSV export).
    """
    from mmm_os.models import Job  # local import to avoid a module-level cycle

    job = session.scalar(select(Job).where(Job.tenant_id == tenant_id, Job.id == job_id))
    if job is None or job.file_id is None:
        return None, []
    file = session.scalar(select(File).where(File.tenant_id == tenant_id, File.id == job.file_id))
    if file is None:
        return None, []
    query = (
        select(OutputRow)
        .where(OutputRow.tenant_id == tenant_id, OutputRow.source_file_id == file.id)
        .order_by(OutputRow.source_row)
    )
    if limit is not None:
        query = query.limit(limit)
    rows = session.scalars(query).all()
    return file, list(rows)
