"""Stack assembly, panel validation, and publish (Phase 16.1 / 16.4)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import Stack, StackRow
from mmm_os.output.service import list_output_rows
from mmm_os.services.tenant_settings import reporting_context
from mmm_os.stack.harmonize import HarmonizationSpec, harmonize_rows
from mmm_os.transform.types import Table
from mmm_os.validation.engine import finalize, validate
from mmm_os.validation.flags import Finding, Flag
from mmm_os.validation.policy import Policy


def assemble_stack(
    session: Session,
    canonical: CanonicalConfig,
    *,
    tenant_id: uuid.UUID,
    name: str,
    description: str | None,
    source_job_ids: list[uuid.UUID],
    spec: HarmonizationSpec,
    grain: str | None = None,
    created_by: uuid.UUID | None = None,
) -> Stack:
    """Assemble a draft Stack from one or more Silver outputs, harmonized (Gold).

    Reads each source job's clean ``output_row`` set, applies the harmonization
    spec, and persists the unified panel as ``stack_row`` records with lineage
    back to each source (CC-3). The Stack starts as a ``draft``.
    """
    frame = reporting_context(session, tenant_id)
    stack = Stack(
        tenant_id=tenant_id,
        name=name,
        description=description,
        version=1,
        lifecycle_status="draft",
        grain=grain,
        reporting_currency=frame.currency,
        reporting_timezone=frame.timezone,
        source_job_ids=[str(j) for j in source_job_ids],
        created_by=created_by,
    )
    session.add(stack)
    session.flush()

    present: set[str] = set()
    for job_id in source_job_ids:
        file, rows = list_output_rows(session, tenant_id, job_id, limit=None)
        if file is None:
            continue
        harmonized = harmonize_rows([dict(r.data) for r in rows], spec)
        for source_row, harmonized_row in zip(rows, harmonized, strict=True):
            present |= set(harmonized_row)
            session.add(
                StackRow(
                    tenant_id=tenant_id,
                    stack_id=stack.id,
                    stack_version=stack.version,
                    source_job_id=job_id,
                    source_file_id=source_row.source_file_id,
                    source_sheet=source_row.source_sheet,
                    source_row=source_row.source_row,
                    data=harmonized_row,
                )
            )
    stack.schema_contract = {"columns": sorted(present)}
    session.flush()
    return stack


def stack_rows_as_dicts(session: Session, tenant_id: uuid.UUID, stack_id: uuid.UUID) -> Table:
    """Return a stack's panel rows as plain dicts (for validation/stats/export)."""
    rows = session.scalars(
        tenant_scoped_select(StackRow, tenant_id)
        .where(StackRow.stack_id == stack_id)
        .order_by(StackRow.created_at)
    ).all()
    return [dict(r.data) for r in rows]


def _taxonomy_completeness(table: Table, canonical: CanonicalConfig) -> list[Finding]:
    """Flag channel values that do not resolve to the canonical taxonomy (panel check)."""
    tax = canonical.taxonomies.taxonomies.get("channel")
    if tax is None:
        return []
    terms = set(tax.terms)
    findings: list[Finding] = []
    for i, row in enumerate(table):
        value = row.get("channel")
        if not isinstance(value, str) or value in terms:
            continue
        if canonical.taxonomies.resolve("channel", value) is None:
            findings.append(
                Finding(
                    "taxonomy_incomplete",
                    f"channel value {value!r} is not in the canonical taxonomy",
                    {"row": i, "field": "channel", "value": value},
                )
            )
    return findings


def validate_panel(
    table: Table, canonical: CanonicalConfig, policy: Policy | None = None
) -> list[Flag]:
    """Run cross-source panel validation on an assembled stack (Gold gate, CC-15).

    Combines the standard + semantic checks with cross-source panel checks
    (taxonomy completeness). Returns severity-assigned flags.
    """
    active = policy or Policy()
    flags = validate(table, canonical.schema, active)
    flags += finalize(_taxonomy_completeness(table, canonical), active)
    return flags


def list_stacks(session: Session, tenant_id: uuid.UUID) -> list[Stack]:
    """Return a tenant's stacks, newest first."""
    return list(
        session.scalars(
            tenant_scoped_select(Stack, tenant_id).order_by(Stack.created_at.desc())
        ).all()
    )


def get_stack(session: Session, tenant_id: uuid.UUID, stack_id: uuid.UUID) -> Stack | None:
    """Return a stack by id, tenant-scoped."""
    return session.scalar(tenant_scoped_select(Stack, tenant_id).where(Stack.id == stack_id))


def publish_stack(
    session: Session,
    canonical: CanonicalConfig,
    *,
    tenant_id: uuid.UUID,
    stack_id: uuid.UUID,
    force: bool = False,
) -> tuple[Stack | None, list[Flag]]:
    """Publish a stack, gated on panel validation (CC-15). Idempotent (CC-6).

    Returns ``(stack, blocking_flags)``. If there are blocking flags and ``force``
    is false, the stack is left as a draft and the blocking flags are returned.
    """
    stack = get_stack(session, tenant_id, stack_id)
    if stack is None:
        return None, []
    table = stack_rows_as_dicts(session, tenant_id, stack_id)
    flags = validate_panel(table, canonical)
    blocking = [f for f in flags if f.severity == "blocking"]
    if blocking and not force:
        return stack, blocking
    stack.lifecycle_status = "published"
    session.flush()
    return stack, []
