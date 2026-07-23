"""Data retention + purge engine (Phase 10, P10-1).

Deletes data past its retention window, per data class, tenant-scoped (CC-1). A raw
file's purge **cascades** its derived data (sheets, profiles, jobs, events, flags,
suggestions, output rows) and its immutable-raw bytes — the governance-authorized
exception to CC-2. Other classes (LLM usage, sync runs, read notifications, and
optionally the audit log) are purged standalone. Idempotent (CC-6): re-running only
removes what is now expired.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mmm_os.core.config import Settings
from mmm_os.ingestion.service import storage_key_for
from mmm_os.models import (
    Assignment,
    AuditLog,
    Comment,
    File,
    Job,
    JobEvent,
    LlmUsage,
    Notification,
    OutputRow,
    Profile,
    Sheet,
    Suggestion,
    SyncRun,
    ValidationFlag,
)
from mmm_os.storage.base import ObjectStorage


@dataclass(frozen=True)
class RetentionPolicy:
    """Retention windows (days) per data class; 0 = keep forever."""

    raw_file_days: int = 365
    llm_usage_days: int = 90
    sync_run_days: int = 180
    notification_days: int = 90
    audit_log_days: int = 0

    @classmethod
    def from_settings(cls, settings: Settings) -> RetentionPolicy:
        """Build the policy from application settings."""
        return cls(
            raw_file_days=settings.retention_raw_file_days,
            llm_usage_days=settings.retention_llm_usage_days,
            sync_run_days=settings.retention_sync_run_days,
            notification_days=settings.retention_notification_days,
            audit_log_days=settings.retention_audit_log_days,
        )


def _cutoff(now: datetime, days: int) -> datetime | None:
    """Return the cutoff timestamp for a retention window, or None if disabled."""
    return None if days <= 0 else now - timedelta(days=days)


def delete_file_data(
    session: Session, storage: ObjectStorage, tenant_id: uuid.UUID, file: File
) -> None:
    """Delete a file and all data derived from it (retention + erasure cascade).

    Explicit (not relying on DB cascade) and ordered children-first so it works
    regardless of dialect FK enforcement. Also removes the immutable-raw bytes.
    """
    sheets = list(
        session.scalars(select(Sheet).where(Sheet.tenant_id == tenant_id, Sheet.file_id == file.id))
    )
    sheet_ids = {s.id for s in sheets}

    # Suggestions reference a sheet by id inside their JSON payload (no FK).
    if sheet_ids:
        for suggestion in session.scalars(
            select(Suggestion).where(Suggestion.tenant_id == tenant_id)
        ):
            payload = suggestion.payload if isinstance(suggestion.payload, dict) else {}
            ref = payload.get("sheet_id")
            if ref is not None and uuid.UUID(str(ref)) in sheet_ids:
                session.delete(suggestion)

    jobs = list(
        session.scalars(select(Job).where(Job.tenant_id == tenant_id, Job.file_id == file.id))
    )
    for job in jobs:
        session.execute(delete(JobEvent).where(JobEvent.job_id == job.id))
        session.execute(delete(ValidationFlag).where(ValidationFlag.job_id == job.id))
    for job in jobs:
        session.delete(job)

    if sheet_ids:
        session.execute(delete(Profile).where(Profile.sheet_id.in_(sheet_ids)))
    session.execute(
        delete(OutputRow).where(
            OutputRow.tenant_id == tenant_id, OutputRow.source_file_id == file.id
        )
    )
    # Collaboration objects targeting this file.
    for model in (Comment, Assignment, Notification):
        session.execute(
            delete(model).where(model.tenant_id == tenant_id, model.target_id == file.id)
        )
    for sheet in sheets:
        session.delete(sheet)

    storage.delete(storage_key_for(file))
    session.delete(file)


def run_retention(
    session: Session,
    storage: ObjectStorage,
    *,
    now: datetime,
    policy: RetentionPolicy,
) -> dict[str, int]:
    """Purge expired data across all classes; return a per-class count of rows removed."""
    summary: dict[str, int] = {}

    file_cut = _cutoff(now, policy.raw_file_days)
    files_purged = 0
    if file_cut is not None:
        for file in list(session.scalars(select(File).where(File.created_at < file_cut))):
            delete_file_data(session, storage, file.tenant_id, file)
            files_purged += 1
    summary["raw_file"] = files_purged

    summary["llm_usage"] = _purge_by_created_at(
        session, LlmUsage, _cutoff(now, policy.llm_usage_days)
    )
    summary["sync_run"] = _purge_by_created_at(
        session, SyncRun, _cutoff(now, policy.sync_run_days)
    )
    summary["audit_log"] = _purge_by_created_at(
        session, AuditLog, _cutoff(now, policy.audit_log_days)
    )

    notif_cut = _cutoff(now, policy.notification_days)
    if notif_cut is not None:
        result = session.execute(
            delete(Notification).where(
                Notification.read.is_(True), Notification.created_at < notif_cut
            )
        )
        summary["notification"] = int(result.rowcount or 0)  # type: ignore[attr-defined]
    else:
        summary["notification"] = 0

    session.flush()
    return summary


def _purge_by_created_at(session: Session, model: type, cutoff: datetime | None) -> int:
    """Delete rows of ``model`` created before ``cutoff`` (no-op if disabled)."""
    if cutoff is None:
        return 0
    result = session.execute(delete(model).where(model.created_at < cutoff))  # type: ignore[attr-defined]
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
