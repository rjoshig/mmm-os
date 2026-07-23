"""Full-pipeline orchestration: detect → map → transform → validate → output.

Sequences the per-stage services into one call so a file can be processed end to
end without a human driving each step. The one-time human step is column mapping:
the first file from a new source has no saved mapping, so the pipeline auto-maps
by signature and saves it; if even the signature is unknown it reports
``needs_mapping`` and skips that sheet. Every subsequent file with the same
headers then runs unattended (CC-9 source-agnostic, config-as-data reuse).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.mapping.engine import apply_mapping
from mmm_os.mapping.service import auto_map_sheet, resolve_mapping, save_sheet_mapping
from mmm_os.mapping.signature import column_signature
from mmm_os.models import File, Job, Sheet
from mmm_os.models.enums import RuleLayer, Severity
from mmm_os.output import generate_output, prepare_sheet_rows
from mmm_os.storage.base import ObjectStorage
from mmm_os.validation.service import run_validation


@dataclass
class SheetPipelineResult:
    """Per-sheet outcome of a pipeline run."""

    sheet_id: uuid.UUID
    sheet_name: str | None
    needs_mapping: bool
    mapping_config_version: int | None
    missing_required: list[str]
    flag_count: int
    blocked: bool
    output_rows_written: int | None
    rule_set_version: int | None


@dataclass
class PipelineResult:
    """Aggregate outcome of a pipeline run over a file's sheets."""

    file_id: uuid.UUID
    job_id: uuid.UUID
    sheets: list[SheetPipelineResult] = field(default_factory=list)

    @property
    def rows_written(self) -> int:
        """Total clean output rows written across all sheets."""
        return sum(s.output_rows_written or 0 for s in self.sheets)


def _ensure_mapping(
    session: Session,
    canonical: CanonicalConfig,
    *,
    tenant_id: uuid.UUID,
    sheet: Sheet,
) -> tuple[bool, int | None, list[str]]:
    """Resolve (or auto-create+save) a mapping for a sheet.

    Returns ``(resolved, mapping_version, missing_required)``. When no saved
    mapping exists, attempts auto-map-by-signature and persists it so downstream
    stages (and future runs) reuse it. ``resolved`` is False only when even
    auto-map cannot match — i.e. the sheet genuinely needs a human to map once.
    """
    signature = column_signature(sheet.columns)
    mapping = resolve_mapping(session, tenant_id, signature)
    if not mapping:
        # First sight of this column structure: try to auto-apply a saved config.
        auto = auto_map_sheet(session, tenant_id, sheet, canonical.schema)
        if not auto.matched or not auto.result:
            return False, None, []
        save_sheet_mapping(
            session,
            tenant_id=tenant_id,
            sheet=sheet,
            name=f"auto-{sheet.id}",
            mapping=auto.mapping,
            layer=RuleLayer.CUSTOMER.value,
        )
        mapping = auto.mapping

    result = apply_mapping(sheet.columns, mapping, canonical.schema)
    version = _latest_mapping_version(session, tenant_id, signature)
    return True, version, result.missing_required


def _latest_mapping_version(
    session: Session, tenant_id: uuid.UUID, signature: str
) -> int | None:
    from sqlalchemy import func

    from mmm_os.models import MappingConfig  # local import avoids a cycle

    return session.scalar(
        select(func.max(MappingConfig.version)).where(
            MappingConfig.tenant_id == tenant_id,
            MappingConfig.file_signature == signature,
            MappingConfig.layer == RuleLayer.CUSTOMER.value,
            MappingConfig.is_active.is_(True),
        )
    )


def run_pipeline(
    session: Session,
    storage: ObjectStorage,
    canonical: CanonicalConfig,
    *,
    tenant_id: uuid.UUID,
    file_id: uuid.UUID,
    row_limit: int = 1000,
) -> PipelineResult:
    """Run the full pipeline over every sheet in a file.

    Args:
        session: The database session.
        storage: Object-storage backend (for reading raw rows).
        canonical: Canonical schema/taxonomies.
        tenant_id: The owning tenant.
        file_id: The file to process.
        row_limit: Max raw rows loaded per sheet.

    Returns:
        A per-sheet pipeline summary.

    Raises:
        ValueError: If the file or its job is not found.
    """
    file = session.scalar(tenant_scoped_select(File, tenant_id).where(File.id == file_id))
    if file is None:
        raise ValueError("file not found")
    job = session.scalar(
        select(Job).where(Job.tenant_id == tenant_id, Job.file_id == file.id).order_by(
            Job.created_at.desc()
        )
    )
    if job is None:
        raise ValueError("job not found")

    sheets = session.scalars(
        select(Sheet)
        .where(Sheet.tenant_id == tenant_id, Sheet.file_id == file.id)
        .order_by(Sheet.sheet_index)
    ).all()

    result = PipelineResult(file_id=file.id, job_id=job.id)
    for sheet in sheets:
        resolved, mapping_version, missing = _ensure_mapping(
            session, canonical, tenant_id=tenant_id, sheet=sheet
        )
        if not resolved:
            result.sheets.append(
                SheetPipelineResult(
                    sheet_id=sheet.id,
                    sheet_name=sheet.sheet_name,
                    needs_mapping=True,
                    mapping_config_version=None,
                    missing_required=[],
                    flag_count=0,
                    blocked=False,
                    output_rows_written=None,
                    rule_set_version=None,
                )
            )
            continue

        prepared = prepare_sheet_rows(
            session, storage, canonical, tenant_id=tenant_id, sheet_id=sheet.id, limit=row_limit
        )
        flags, _blocked = run_validation(
            session,
            tenant_id=tenant_id,
            job_id=job.id,
            table=prepared.rows,
            schema=canonical.schema,
        )
        # Freshly persisted flags are review_status=open, so blocking severity ⇒ blocked.
        blocked = any(f.severity == Severity.BLOCKING.value for f in flags)

        written: int | None = None
        if not blocked:
            written = generate_output(
                session, tenant_id=tenant_id, job_id=job.id, prepared=prepared
            )

        result.sheets.append(
            SheetPipelineResult(
                sheet_id=sheet.id,
                sheet_name=sheet.sheet_name,
                needs_mapping=False,
                mapping_config_version=mapping_version,
                missing_required=missing,
                flag_count=len(flags),
                blocked=blocked,
                output_rows_written=written,
                rule_set_version=prepared.rule_set_version,
            )
        )

    session.commit()
    return result
