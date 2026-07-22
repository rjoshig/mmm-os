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

    Returns:
        The persisted flags and whether output is blocked (CC — a blocking flag).
    """
    active = policy or Policy()
    flags = validate(table, schema, active)
    if anomaly_measure:
        flags += finalize(detect_anomalies(table, anomaly_measure, group_by=group_by), active)
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


def list_flags(
    session: Session, tenant_id: uuid.UUID, job_id: uuid.UUID
) -> Sequence[ValidationFlag]:
    """Return a job's validation flags, tenant-scoped."""
    return session.scalars(
        tenant_scoped_select(ValidationFlag, tenant_id).where(ValidationFlag.job_id == job_id)
    ).all()
