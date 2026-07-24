"""Validation service: run checks + anomaly, persist flags, manage review (P4-5)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from mmm_os.canonical.models import CanonicalSchema
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import ValidationFlag
from mmm_os.models.enums import ReviewStatus
from mmm_os.models.mixins import utcnow
from mmm_os.transform.types import Table
from mmm_os.validation.anomaly import detect_anomalies
from mmm_os.validation.custom import ValidationRuleSpec, run_custom_checks, run_validation_rules
from mmm_os.validation.engine import finalize, validate
from mmm_os.validation.flags import Flag
from mmm_os.validation.policy import Policy, is_blocked

_RESOLVED_STATES = {ReviewStatus.RESOLVED.value, ReviewStatus.OVERRIDDEN.value}


def persist_flags(
    session: Session, tenant_id: uuid.UUID, job_id: uuid.UUID, flags: list[Flag]
) -> list[ValidationFlag]:
    """Persist flags as ``validation_flag`` rows (review status ``open``)."""
    records: list[ValidationFlag] = []
    for flag in flags:
        record = ValidationFlag(
            tenant_id=tenant_id,
            job_id=job_id,
            severity=flag.severity,
            location={**flag.location, "check": flag.check},
            description=flag.description,
            review_status=ReviewStatus.OPEN.value,
        )
        session.add(record)
        records.append(record)
    session.flush()
    return records


def run_validation(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    table: Table,
    schema: CanonicalSchema,
    policy: Policy | None = None,
    anomaly_measure: str | None = None,
    group_by: str | None = None,
    custom_check_exprs: Sequence[tuple[str, str]] | None = None,
    rules: Sequence[ValidationRuleSpec] | None = None,
) -> tuple[list[ValidationFlag], bool]:
    """Validate records, detect anomalies, persist flags, and report blocking.

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        job_id: The job the flags attach to.
        table: The records to validate.
        schema: The canonical schema.
        policy: Optional severity policy.
        anomaly_measure: Optional measure to run anomaly detection on.
        group_by: Optional dimension to slice anomaly detection by.
        custom_check_exprs: Optional tenant custom checks as ``(name, expression)``
            pairs (Phase 21) evaluated per row via the sandbox.
        rules: Optional first-class tenant validation rules (Part 3), each carrying
            its own severity, evaluated per row via the sandbox.

    Returns:
        The persisted flags and whether output is blocked (CC — a blocking flag).
    """
    active = policy or Policy()
    flags = validate(table, schema, active)
    if anomaly_measure:
        flags += finalize(detect_anomalies(table, anomaly_measure, group_by=group_by), active)
    if custom_check_exprs:
        flags += finalize(run_custom_checks(table, custom_check_exprs), active)
    if rules:
        # Tenant validation rules carry their own severity (applied directly).
        flags += run_validation_rules(table, rules)
    records = persist_flags(session, tenant_id, job_id, flags)
    return records, is_blocked(flags)


def review_flag(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    flag_id: uuid.UUID,
    status: str,
    resolved_by: uuid.UUID | None = None,
) -> ValidationFlag | None:
    """Record a human review decision on a flag (P4-5).

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        flag_id: The flag to review.
        status: The new review status (acknowledged/resolved/overridden).
        resolved_by: The user id resolving/overriding (recorded with the time).

    Returns:
        The updated flag, or ``None`` if it does not exist for this tenant.
    """
    flag = session.scalar(
        tenant_scoped_select(ValidationFlag, tenant_id).where(ValidationFlag.id == flag_id)
    )
    if flag is None:
        return None
    flag.review_status = status
    if status in _RESOLVED_STATES:
        flag.resolved_by = resolved_by
        flag.resolved_at = utcnow()
    session.flush()
    return flag


def review_flags_bulk(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    flag_ids: Sequence[uuid.UUID],
    status: str,
    resolved_by: uuid.UUID | None = None,
) -> list[ValidationFlag]:
    """Apply one review decision to many flags of a job in a single transaction.

    Only flags that belong to ``job_id`` for this tenant and appear in ``flag_ids``
    are updated; unknown or cross-job ids are silently ignored. Used to resolve a
    whole cluster of similar flags at once (P4-5, Cycle-1 bulk resolve).

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        job_id: The job the flags must belong to.
        flag_ids: The flags to review.
        status: The new review status (acknowledged/resolved/overridden).
        resolved_by: The user id resolving/overriding (recorded with the time).

    Returns:
        The updated flags (in no particular order).
    """
    wanted = set(flag_ids)
    flags = session.scalars(
        tenant_scoped_select(ValidationFlag, tenant_id)
        .where(ValidationFlag.job_id == job_id)
        .where(ValidationFlag.id.in_(wanted))
    ).all()
    now = utcnow()
    updated: list[ValidationFlag] = []
    for flag in flags:
        flag.review_status = status
        if status in _RESOLVED_STATES:
            flag.resolved_by = resolved_by
            flag.resolved_at = now
        updated.append(flag)
    session.flush()
    return updated


def list_flags(
    session: Session, tenant_id: uuid.UUID, job_id: uuid.UUID
) -> Sequence[ValidationFlag]:
    """Return a job's validation flags, tenant-scoped."""
    return session.scalars(
        tenant_scoped_select(ValidationFlag, tenant_id).where(ValidationFlag.job_id == job_id)
    ).all()
