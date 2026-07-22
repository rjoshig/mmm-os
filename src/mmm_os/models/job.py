"""Job, job-event, validation-flag, and suggestion models (observability + review)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.enums import JobStatus, ReviewStatus, Severity, SuggestionState
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Job(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A processing run over a file/batch. Async-ready from Phase 0."""

    __tablename__ = "job"

    file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("file.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.PENDING.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class JobEvent(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A per-stage status/timing/error record for a job (observability, CC-7)."""

    __tablename__ = "job_event"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ValidationFlag(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """An issue found during validation, with location, severity, and review status."""

    __tablename__ = "validation_flag"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(32), nullable=False, default=Severity.WARNING.value
    )
    location: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReviewStatus.OPEN.value
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Suggestion(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """An AI suggestion + confidence + rationale + accept/reject state (CC-5, Phase 5)."""

    __tablename__ = "suggestion"

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("job.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    rationale: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SuggestionState.PENDING.value
    )
