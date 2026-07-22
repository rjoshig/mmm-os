"""AI suggestion routes: request suggestions and accept/reject them (05.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.ai import LLMClient
from mmm_os.ai.config import load_llm_config
from mmm_os.ai.service import (
    accept_suggestion,
    list_suggestions_for_sheet,
    persist_mapping_suggestions,
    profile_input_for_sheet,
    reject_suggestion,
)
from mmm_os.ai.suggestions import SuggestionService
from mmm_os.api.deps import get_canonical, get_llm_client
from mmm_os.canonical import CanonicalConfig
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.models import Profile, Sheet
from mmm_os.schemas.ai import AcceptResponse, SuggestionRead, SuggestMappingResponse

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
) -> AcceptResponse:
    """Accept a suggestion; a mapping suggestion is written into the config store (P5-8).

    Args:
        tenant_id: The owning tenant.
        suggestion_id: The suggestion to accept.
        session: Database session (injected).

    Returns:
        The accepted suggestion and any resulting mapping-config version.

    Raises:
        HTTPException: 404 if the suggestion does not exist for this tenant.
    """
    result = accept_suggestion(session, tenant_id, suggestion_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="suggestion not found")
    suggestion, version = result
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
) -> SuggestionRead:
    """Reject a suggestion (records the decision; writes no config)."""
    suggestion = reject_suggestion(session, tenant_id, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="suggestion not found")
    session.commit()
    return SuggestionRead.model_validate(suggestion)
