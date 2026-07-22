"""Suggestion persistence and human ratification (P5-6, P5-7, P5-8, CC-5).

Persists suggestions with their confidence + rationale, and turns a human
*accept* into a real config write (mapping config, Phase 2). The AI never writes
committed config — only the accept action does.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from mmm_os.ai.config import LLMConfig
from mmm_os.ai.suggestions import MappingSuggestion
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.mapping.service import resolve_mapping, save_sheet_mapping
from mmm_os.mapping.signature import column_signature
from mmm_os.models import Profile, Sheet, Suggestion
from mmm_os.models.enums import SuggestionKind, SuggestionState


def disposition(confidence: float, config: LLMConfig) -> str:
    """Classify a suggestion by confidence (auto_fill / review / low)."""
    if confidence >= config.confidence_autofill:
        return "auto_fill"
    if confidence >= config.confidence_flag:
        return "review"
    return "low"


def profile_input_for_sheet(sheet: Sheet, profile: Profile | None) -> list[dict[str, Any]]:
    """Build the profile-only input for suggestions (distinct values + stats).

    Args:
        sheet: The detected sheet (column names + types).
        profile: The sheet's profile, if computed.

    Returns:
        One entry per column with name, type, and (if available) sample values,
        distinct count, and null rate — never raw rows (P5-1).
    """
    stats_by_name: dict[str, dict[str, Any]] = {}
    if profile is not None:
        for stat in profile.column_stats.get("columns", []):
            stats_by_name[str(stat.get("name"))] = stat

    columns: list[dict[str, Any]] = []
    for column in sheet.columns:
        name = str(column.get("name"))
        stat = stats_by_name.get(name, {})
        columns.append(
            {
                "name": name,
                "type": column.get("type"),
                "sample_values": stat.get("sample_values", []),
                "distinct_count": stat.get("distinct_count"),
                "null_rate": stat.get("null_rate"),
            }
        )
    return columns


def persist_mapping_suggestions(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    suggestions: list[MappingSuggestion],
    config: LLMConfig,
) -> list[Suggestion]:
    """Persist mapping suggestions as pending, with confidence + rationale (P5-7)."""
    records: list[Suggestion] = []
    for suggestion in suggestions:
        record = Suggestion(
            tenant_id=tenant_id,
            kind=SuggestionKind.MAPPING.value,
            payload={
                "sheet_id": str(sheet_id),
                "source_column": suggestion.source_column,
                "canonical_field": suggestion.canonical_field,
                "disposition": disposition(suggestion.confidence, config),
            },
            confidence=suggestion.confidence,
            rationale=suggestion.rationale,
            state=SuggestionState.PENDING.value,
        )
        session.add(record)
        records.append(record)
    session.flush()
    return records


def _get_suggestion(
    session: Session, tenant_id: uuid.UUID, suggestion_id: uuid.UUID
) -> Suggestion | None:
    return session.scalar(
        tenant_scoped_select(Suggestion, tenant_id).where(Suggestion.id == suggestion_id)
    )


def accept_suggestion(
    session: Session, tenant_id: uuid.UUID, suggestion_id: uuid.UUID
) -> tuple[Suggestion, int | None] | None:
    """Accept a suggestion, writing a mapping suggestion into the config store (P5-8).

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        suggestion_id: The suggestion to accept.

    Returns:
        The accepted suggestion and the resulting mapping-config version (or
        ``None`` version for non-mapping kinds); ``None`` if the suggestion does
        not exist for this tenant.
    """
    suggestion = _get_suggestion(session, tenant_id, suggestion_id)
    if suggestion is None:
        return None

    version: int | None = None
    if suggestion.kind == SuggestionKind.MAPPING.value:
        payload = suggestion.payload
        sheet = session.scalar(
            tenant_scoped_select(Sheet, tenant_id).where(
                Sheet.id == uuid.UUID(str(payload["sheet_id"]))
            )
        )
        source = payload.get("source_column")
        field = payload.get("canonical_field")
        if sheet is not None and source and field:
            merged = resolve_mapping(session, tenant_id, column_signature(sheet.columns))
            merged[str(source)] = str(field)
            config = save_sheet_mapping(
                session, tenant_id=tenant_id, sheet=sheet, name="ai-accepted", mapping=merged
            )
            version = config.version

    suggestion.state = SuggestionState.ACCEPTED.value
    session.flush()
    return suggestion, version


def reject_suggestion(
    session: Session, tenant_id: uuid.UUID, suggestion_id: uuid.UUID
) -> Suggestion | None:
    """Reject a suggestion (records the decision; writes nothing to config)."""
    suggestion = _get_suggestion(session, tenant_id, suggestion_id)
    if suggestion is None:
        return None
    suggestion.state = SuggestionState.REJECTED.value
    session.flush()
    return suggestion


def list_suggestions_for_sheet(
    session: Session, tenant_id: uuid.UUID, sheet_id: uuid.UUID
) -> Sequence[Suggestion]:
    """List suggestions whose payload references a sheet, tenant-scoped."""
    all_suggestions = session.scalars(tenant_scoped_select(Suggestion, tenant_id)).all()
    target = str(sheet_id)
    return [s for s in all_suggestions if str(s.payload.get("sheet_id")) == target]
