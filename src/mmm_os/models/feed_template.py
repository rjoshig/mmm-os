"""Per-customer feed template — a named, reusable file layout (Slice 7.4).

A customer that sends the same 50–60 recurring files each period defines a
**feed template** per layout: its format (delimited / fixed-width), delimiter or
column spec, and the columns it is expected to contain. Templates are stored as
versioned config-as-data (CC-4) so a recognised feed parses and auto-maps the same
way every time, regardless of source.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from mmm_os.db.base import Base
from mmm_os.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FeedTemplate(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A named file layout a customer sends repeatedly."""

    __tablename__ = "feed_template"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # delimited | fixed_width | xlsx
    fmt: Mapped[str] = mapped_column(String(16), nullable=False, default="delimited")
    # For delimited: the delimiter (null = sniff at ingest). Ignored otherwise.
    delimiter: Mapped[str | None] = mapped_column(String(4))
    has_header: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # For fixed_width: [{"name": str, "start": int, "width": int}, ...].
    fixed_fields: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    # The columns a matching feed is expected to contain (drives auto-map by signature).
    expected_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # Optional filename glob (e.g. "sales_*.txt") to auto-match incoming feeds.
    filename_glob: Mapped[str | None] = mapped_column(String(255))
