"""AI suggestion routes: request suggestions and accept/reject them (05.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.ai import LLMClient
from mmm_os.ai.budget import usage_snapshot
from mmm_os.ai.config import load_llm_config
from mmm_os.ai.service import (
    accept_suggestion,
    list_suggestions_for_sheet,
    persist_mapping_suggestions,
    persist_transform_suggestions,
    profile_input_for_sheet,
    reject_suggestion,
)
from mmm_os.ai.suggestions import SuggestionService
from mmm_os.api.deps import get_canonical, get_llm_client, require_auth
from mmm_os.auth.service import Principal
from mmm_os.canonical import CanonicalConfig
from mmm_os.core.config import get_settings
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.models import Job, Profile, Sheet, ValidationFlag
from mmm_os.models.enums import ReviewStatus
from mmm_os.schemas.ai import (
    AcceptResponse,
    LlmUsageRead,
    SuggestionRead,
    SuggestMappingResponse,
)

router = APIRouter(prefix="/api/v1", tags=["ai"])


@router.post(
    "/tenants/{tenant_id}/sheets/{sheet_id}/suggest-mapping",
    status_code=status.HTTP_201_CREATED,
    response_model=SuggestMappingResponse,
)
def suggest_mapping(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
    client: LLMClient = Depends(get_llm_client),
) -> SuggestMappingResponse:
    """Draft canonical-field mapping suggestions for a sheet from its profile.

    Args:
        tenant_id: The owning tenant.
        sheet_id: The sheet to suggest mappings for.
        session: Database session (injected).
        canonical: Canonical schema/taxonomies (injected).
        client: LLM client (injected; 503 if the LLM is disabled).

    Returns:
        The persisted, pending suggestions (never auto-committed).

    Raises:
        HTTPException: 404 if the sheet does not exist for this tenant.
    """
    sheet = session.scalar(tenant_scoped_select(Sheet, tenant_id).where(Sheet.id == sheet_id))
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sheet not found")

    profile = session.scalar(
        tenant_scoped_select(Profile, tenant_id).where(Profile.sheet_id == sheet_id)
    )
    profile_columns = profile_input_for_sheet(sheet, profile)
    canonical_fields = [f.name for f in (*canonical.schema.dimensions, *canonical.schema.measures)]

    suggestions = SuggestionService(client).suggest_column_mappings(
        profile_columns, canonical_fields
    )
    records = persist_mapping_suggestions(
        session,
        tenant_id=tenant_id,
        sheet_id=sheet_id,
        suggestions=suggestions,
        config=load_llm_config(),
    )
    session.commit()
    return SuggestMappingResponse(suggestions=[SuggestionRead.model_validate(r) for r in records])


def _open_flag_issues(session: Session, tenant_id: uuid.UUID, sheet: Sheet) -> list[dict[str, str]]:
    """Distinct (check, field) of open flags on the sheet's file's latest job (remediation)."""
    job = session.scalar(
        tenant_scoped_select(Job, tenant_id)
        .where(Job.file_id == sheet.file_id)
        .order_by(Job.created_at.desc())
    )
    if job is None:
        return []
    flags = session.scalars(
        tenant_scoped_select(ValidationFlag, tenant_id).where(ValidationFlag.job_id == job.id)
    ).all()
    resolved = {ReviewStatus.RESOLVED.value, ReviewStatus.OVERRIDDEN.value}
    seen: set[tuple[str, str]] = set()
    issues: list[dict[str, str]] = []
    for flag in flags:
        if flag.review_status in resolved:
            continue
        key = (str(flag.location.get("check", "")), str(flag.location.get("field", "")))
        if key in seen:
            continue
        seen.add(key)
        issues.append({"check": key[0], "field": key[1]})
    return issues


@router.post(
    "/tenants/{tenant_id}/sheets/{sheet_id}/suggest-transforms",
    status_code=status.HTTP_201_CREATED,
    response_model=SuggestMappingResponse,
)
def suggest_transforms(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    remediate: bool = False,
    session: Session = Depends(get_session),
    canonical: CanonicalConfig = Depends(get_canonical),
    client: LLMClient = Depends(get_llm_client),
) -> SuggestMappingResponse:
    """Draft AI transform-rule suggestions for a sheet (Cycle 4, suggest-not-decide).

    Proposes declarative cleaning rules from the column profile; with
    ``remediate=true`` it also feeds the sheet's open validation flags so the model
    proposes fixes. Suggestions are persisted pending — accepting one appends the
    rule to the sheet's rule set (CC-5).

    Raises:
        HTTPException: 404 if the sheet does not exist for this tenant.
    """
    sheet = session.scalar(tenant_scoped_select(Sheet, tenant_id).where(Sheet.id == sheet_id))
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sheet not found")
    profile = session.scalar(
        tenant_scoped_select(Profile, tenant_id).where(Profile.sheet_id == sheet_id)
    )
    profile_columns = profile_input_for_sheet(sheet, profile)
    schema = canonical.schema
    canonical_fields = [
        f.name for f in (*schema.dimensions, *schema.measures, *schema.factors)
    ]
    issues = _open_flag_issues(session, tenant_id, sheet) if remediate else []

    suggestions = SuggestionService(client).suggest_transform_rules(
        profile_columns, canonical_fields, issues
    )
    records = persist_transform_suggestions(
        session,
        tenant_id=tenant_id,
        sheet_id=sheet_id,
        suggestions=suggestions,
        config=load_llm_config(),
    )
    session.commit()
    return SuggestMappingResponse(suggestions=[SuggestionRead.model_validate(r) for r in records])


@router.get("/tenants/{tenant_id}/llm-usage", response_model=LlmUsageRead)
def llm_usage(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> LlmUsageRead:
    """Return the tenant's LLM usage over the last 24h vs its caps (CC-13)."""
    snap = usage_snapshot(session, tenant_id, get_settings())
    return LlmUsageRead(
        calls=snap.calls,
        tokens=snap.tokens,
        call_cap=snap.call_cap,
        token_cap=snap.token_cap,
        over_budget=snap.over_budget,
    )


@router.get(
    "/tenants/{tenant_id}/sheets/{sheet_id}/suggestions",
    response_model=list[SuggestionRead],
)
def list_suggestions(
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[SuggestionRead]:
    """List a sheet's suggestions."""
    return [
        SuggestionRead.model_validate(s)
        for s in list_suggestions_for_sheet(session, tenant_id, sheet_id)
    ]


@router.post(
    "/tenants/{tenant_id}/suggestions/{suggestion_id}/accept",
    response_model=AcceptResponse,
)
def accept(
    tenant_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    session: Session = Depends(get_session),
    principal: Principal | None = Depends(require_auth),
) -> AcceptResponse:
    """Accept a suggestion; a mapping suggestion is written into the config store (P5-8).

    Args:
        tenant_id: The owning tenant.
        suggestion_id: The suggestion to accept.
        session: Database session (injected).
        principal: The authenticated actor (recorded in the audit log).

    Returns:
        The accepted suggestion and any resulting mapping-config version.

    Raises:
        HTTPException: 404 if the suggestion does not exist for this tenant.
    """
    result = accept_suggestion(session, tenant_id, suggestion_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="suggestion not found")
    suggestion, version = result
    record_audit(
        session,
        tenant_id=tenant_id,
        action="suggestion.accept",
        principal=principal,
        target_type="suggestion",
        target_id=str(suggestion_id),
        detail={"mapping_config_version": version},
    )
    session.commit()
    return AcceptResponse(
        suggestion=SuggestionRead.model_validate(suggestion), mapping_config_version=version
    )


@router.post(
    "/tenants/{tenant_id}/suggestions/{suggestion_id}/reject",
    response_model=SuggestionRead,
)
def reject(
    tenant_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    session: Session = Depends(get_session),
    principal: Principal | None = Depends(require_auth),
) -> SuggestionRead:
    """Reject a suggestion (records the decision; writes no config)."""
    suggestion = reject_suggestion(session, tenant_id, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="suggestion not found")
    record_audit(
        session,
        tenant_id=tenant_id,
        action="suggestion.reject",
        principal=principal,
        target_type="suggestion",
        target_id=str(suggestion_id),
    )
    session.commit()
    return SuggestionRead.model_validate(suggestion)
