"""Feed-template routes (Slice 7.4): define a customer's recurring file layouts.

Admin-gated, tenant-scoped. A template captures how a recurring feed is parsed
(delimited / fixed-width) and which columns it should contain, so the same 50–60
files a customer sends every period parse — and auto-map by column signature — the
same way every time (config-as-data, CC-4).
"""

from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from mmm_os.authz import Permission, require_permission
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.ingestion.parsing import ParseError, read_preview
from mmm_os.ingestion.templates import parse_options_for
from mmm_os.mapping.signature import column_signature, normalize_name
from mmm_os.models import FeedTemplate
from mmm_os.schemas.feed_template import (
    FeedTemplateCreate,
    FeedTemplatePreview,
    FeedTemplateRead,
)

router = APIRouter(prefix="/api/v1", tags=["feed-templates"])

_ADMIN = Depends(require_permission(Permission.ADMIN))

_PREVIEW_ROWS = 20


def _get_template(
    session: Session, tenant_id: uuid.UUID, template_id: uuid.UUID
) -> FeedTemplate:
    template = session.scalar(
        tenant_scoped_select(FeedTemplate, tenant_id).where(FeedTemplate.id == template_id)
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="feed template not found")
    return template


@router.post(
    "/tenants/{tenant_id}/feed-templates",
    status_code=status.HTTP_201_CREATED,
    response_model=FeedTemplateRead,
    dependencies=[_ADMIN],
)
def create_feed_template(
    tenant_id: uuid.UUID,
    body: FeedTemplateCreate,
    session: Session = Depends(get_session),
) -> FeedTemplateRead:
    """Define a customer feed template (a reusable file layout)."""
    if body.fmt == "fixed_width" and not body.fixed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fixed_width templates require fixed_fields",
        )
    template = FeedTemplate(
        tenant_id=tenant_id,
        name=body.name,
        fmt=body.fmt,
        delimiter=body.delimiter,
        has_header=body.has_header,
        fixed_fields=[f.model_dump() for f in body.fixed_fields],
        expected_columns=body.expected_columns,
        filename_glob=body.filename_glob,
    )
    session.add(template)
    session.commit()
    return FeedTemplateRead.model_validate(template)


@router.get(
    "/tenants/{tenant_id}/feed-templates",
    response_model=list[FeedTemplateRead],
    dependencies=[_ADMIN],
)
def list_feed_templates(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[FeedTemplateRead]:
    """List a customer's feed templates."""
    templates = session.scalars(
        tenant_scoped_select(FeedTemplate, tenant_id).order_by(FeedTemplate.created_at)
    ).all()
    return [FeedTemplateRead.model_validate(t) for t in templates]


@router.delete(
    "/tenants/{tenant_id}/feed-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ADMIN],
)
def delete_feed_template(
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> None:
    """Delete a customer's feed template."""
    template = _get_template(session, tenant_id, template_id)
    session.delete(template)
    session.commit()


@router.post(
    "/tenants/{tenant_id}/feed-templates/{template_id}/preview",
    response_model=FeedTemplatePreview,
    dependencies=[_ADMIN],
)
async def preview_feed_template(
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    upload: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> FeedTemplatePreview:
    """Parse a sample file with a template's layout and return a bounded preview.

    Also reports whether the parsed header matches the template's expected-column
    signature (drives auto-map-by-signature in onboarding).

    Raises:
        HTTPException: 400 if the sample cannot be parsed with the template.
    """
    template = _get_template(session, tenant_id, template_id)
    options = parse_options_for(template)
    raw = await upload.read()
    filename = upload.filename or "sample.txt"
    try:
        sheets = read_preview(io.BytesIO(raw), filename, _PREVIEW_ROWS + 1, options)
    except ParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    sheet = sheets[0] if sheets else None
    if sheet is None or not sheet.rows:
        return FeedTemplatePreview(columns=[], rows=[], row_count=0)

    header = [c or "" for c in sheet.rows[0]]
    data = sheet.rows[1 : _PREVIEW_ROWS + 1]

    matches: bool | None = None
    if template.expected_columns:
        parsed_sig = column_signature([{"name": c} for c in header])
        expected_sig = "|".join(sorted({normalize_name(c) for c in template.expected_columns}))
        matches = parsed_sig == expected_sig

    return FeedTemplatePreview(
        columns=header,
        rows=data,
        row_count=len(data),
        signature_matches=matches,
    )
