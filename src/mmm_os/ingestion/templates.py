"""Bridge a stored FeedTemplate to low-level parse options (Slice 7.4)."""

from __future__ import annotations

from mmm_os.ingestion.parsing import FixedWidthField, ParseOptions
from mmm_os.models import FeedTemplate


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
