"""Collaboration models (Phase 13): work assignment for the review queue.

Tenant-scoped (CC-1). An assignment routes a unit of work (a file or sheet) to a
teammate so the team can hand work off — "assigned to me" / "needs review".
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Assignment(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A unit of review work assigned to a tenant user (Phase 13.4)."""

    __tablename__ = "assignment"

    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # file | sheet
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    assignee_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")  # open | done
    note: Mapped[str | None] = mapped_column(String(500))


class Comment(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """An in-context note on an object (file/sheet/flag) — the activity feed (Phase 13.5)."""

    __tablename__ = "comment"

    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # file | sheet | flag
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL")
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)


class Notification(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """An in-app notification for a user (mention / assignment / publish; Phase 13.5)."""

    __tablename__ = "notification"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)  # mention|assignment|publish
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
