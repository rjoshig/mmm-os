"""Bridge a stored FeedTemplate to low-level parse options + feed matching (7.4/7.7)."""

from __future__ import annotations

import fnmatch
import uuid

from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.ingestion.parsing import FixedWidthField, ParseOptions
from mmm_os.models import FeedTemplate


def resolve_template_for_file(
    session: Session, tenant_id: uuid.UUID, filename: str
) -> FeedTemplate | None:
    """Return the first feed template whose filename glob matches ``filename`` (7.7).

    Templates without a glob never match here (they are applied by column signature
    at mapping time). Match order is by creation time so the earliest-defined
    template wins deterministically.
    """
    templates = session.scalars(
        tenant_scoped_select(FeedTemplate, tenant_id).order_by(FeedTemplate.created_at)
    ).all()
    for template in templates:
        if template.filename_glob and fnmatch.fnmatch(filename, template.filename_glob):
            return template
    return None


def parse_options_for(template: FeedTemplate) -> ParseOptions:
    """Build :class:`ParseOptions` from a customer's stored feed template."""
    fields = tuple(
        FixedWidthField(name=f["name"], start=int(f["start"]), width=int(f["width"]))
        for f in template.fixed_fields
    )
    return ParseOptions(
        fmt=template.fmt,
        delimiter=template.delimiter,
        has_header=template.has_header,
        fixed_fields=fields,
    )
