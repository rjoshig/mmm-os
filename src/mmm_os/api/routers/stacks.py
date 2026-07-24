"""Stage-2 Stack routes: assemble, publish, browse, export (Phase 16)."""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_canonical
from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.output.service import list_output_rows
from mmm_os.schemas.output import MeasureStatsRead
from mmm_os.schemas.stack import (
    HarmonizationSuggestion,
    HarmonizationSuggestionsResponse,
    PublishStackResponse,
    StackCreate,
    StackDetail,
    StackRead,
)
from mmm_os.stack import (
    HarmonizationSpec,
    assemble_stack,
    get_stack,
    list_stacks,
    publish_stack,
    stack_rows_as_dicts,
    suggest_harmonization,
)
from mmm_os.validation.stats import output_statistics

router = APIRouter(prefix="/api/v1", tags=["stacks"])

_WRITE_CONFIG = Depends(require_permission(Permission.WRITE_CONFIG))
_REVIEW = Depends(require_permission(Permission.REVIEW))


def _principal_id(principal: Principal | None) -> uuid.UUID | None:
    return principal.user_id if principal else None


def _stats(table: list[dict[str, object]], canonical: CanonicalConfig) -> list[MeasureStatsRead]:
    stats = output_statistics(table, canonical.schema)
    return [MeasureStatsRead(**vars(m)) for m in stats.measures]


@router.post("/tenants/{tenant_id}/stacks", response_model=StackDetail, status_code=201)
def create_stack_route(
    tenant_id: uuid.UUID,
    body: StackCreate,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
    principal: Principal | None = _WRITE_CONFIG,
) -> StackDetail:
    """Assemble a draft Stack (Gold) from one or more Silver outputs, harmonized."""
    spec = HarmonizationSpec.from_dict(body.harmonization.model_dump())
    stack = assemble_stack(
        session,
        canonical,
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        source_job_ids=body.source_job_ids,
        spec=spec,
        grain=body.grain,
        created_by=_principal_id(principal),
    )
    record_audit(
        session,
        tenant_id=tenant_id,
        action="stack.assemble",
        principal=principal,
        target_type="stack",
        target_id=str(stack.id),
        detail={"name": stack.name, "sources": len(body.source_job_ids)},
    )
    session.commit()
    return _detail(session, canonical, tenant_id, stack.id)


@router.get("/tenants/{tenant_id}/stacks", response_model=list[StackRead])
def list_stacks_route(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[StackRead]:
    """List a tenant's stacks (newest first)."""
    return [StackRead.model_validate(s) for s in list_stacks(session, tenant_id)]


def _detail(
    session: Session, canonical: CanonicalConfig, tenant_id: uuid.UUID, stack_id: uuid.UUID
) -> StackDetail:
    stack = get_stack(session, tenant_id, stack_id)
    if stack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="stack not found")
    table = stack_rows_as_dicts(session, tenant_id, stack_id)
    return StackDetail(
        **StackRead.model_validate(stack).model_dump(),
        row_count=len(table),
        measures=_stats(table, canonical),
    )


@router.get("/tenants/{tenant_id}/stacks/{stack_id}", response_model=StackDetail)
def get_stack_route(
    tenant_id: uuid.UUID,
    stack_id: uuid.UUID,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> StackDetail:
    """Return a stack with its row count + per-measure output statistics."""
    return _detail(session, canonical, tenant_id, stack_id)


@router.post("/tenants/{tenant_id}/stacks/{stack_id}/publish", response_model=PublishStackResponse)
def publish_stack_route(
    tenant_id: uuid.UUID,
    stack_id: uuid.UUID,
    force: bool = False,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
    principal: Principal | None = _REVIEW,
) -> PublishStackResponse:
    """Publish a stack, gated on cross-source panel validation (CC-15)."""
    stack, blocking = publish_stack(
        session, canonical, tenant_id=tenant_id, stack_id=stack_id, force=force
    )
    if stack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="stack not found")
    published = stack.lifecycle_status == "published"
    if published:
        record_audit(
            session,
            tenant_id=tenant_id,
            action="stack.publish",
            principal=principal,
            target_type="stack",
            target_id=str(stack_id),
            detail={"forced": force},
        )
    session.commit()
    return PublishStackResponse(
        stack_id=stack_id,
        lifecycle_status=stack.lifecycle_status,
        published=published,
        blocking_flags=[
            {"check": f.check, "description": f.description, "location": f.location}
            for f in blocking
        ],
    )


@router.post(
    "/tenants/{tenant_id}/stacks/harmonization-suggestions",
    response_model=HarmonizationSuggestionsResponse,
)
def harmonization_suggestions_route(
    tenant_id: uuid.UUID,
    source_job_ids: list[uuid.UUID],
    field: str = "channel",
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
    principal: Principal | None = _WRITE_CONFIG,
) -> HarmonizationSuggestionsResponse:
    """Propose value harmonizations (deterministic-first) across source outputs (CC-5)."""
    table: list[dict[str, object]] = []
    for job_id in source_job_ids:
        _, rows = list_output_rows(session, tenant_id, job_id, limit=None)
        table.extend(dict(r.data) for r in rows)
    suggestions = suggest_harmonization(
        table, canonical.taxonomies, field=field, taxonomy=field
    )
    return HarmonizationSuggestionsResponse(
        field=field,
        suggestions=[HarmonizationSuggestion(**s) for s in suggestions],
    )


@router.get("/tenants/{tenant_id}/stacks/{stack_id}.csv")
def stack_csv_route(
    tenant_id: uuid.UUID,
    stack_id: uuid.UUID,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
) -> StreamingResponse:
    """Stream a stack as model-ready CSV (canonical columns in schema order)."""
    stack = get_stack(session, tenant_id, stack_id)
    if stack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="stack not found")
    table = stack_rows_as_dicts(session, tenant_id, stack_id)
    present: set[str] = set()
    for row in table:
        present |= set(row)
    schema = canonical.schema
    columns: list[str] = []
    for group in (schema.dimensions, schema.measures, schema.factors):
        columns += [f.name for f in group if f.name in present]
    # Include any tenant-extension columns not in the core schema.
    columns += sorted(present - set(columns))

    def _rows() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for row in table:
            writer.writerow([row.get(c, "") for c in columns])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    safe = stack.name.replace(" ", "_")
    return StreamingResponse(
        _rows(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe}_stack.csv"'},
    )
