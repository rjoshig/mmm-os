"""Suggestion service: draft mapping/taxonomy/anomaly suggestions via the LLM.

Wraps an ``LLMClient`` and turns profile inputs into structured suggestions with a
confidence and rationale. No persistence and no auto-commit — that is the human
review loop (``ai/service.py``); the AI only *suggests* (CC-5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mmm_os.ai.client import LLMClient
from mmm_os.ai.prompts import (
    anomaly_prompt,
    mapping_prompt,
    parse_json_response,
    taxonomy_prompt,
)


@dataclass(frozen=True)
class MappingSuggestion:
    """A suggested source-column → canonical-field mapping."""

    source_column: str
    canonical_field: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class TaxonomySuggestion:
    """A suggested canonical taxonomy term for raw values."""

    canonical_term: str
    confidence: float
    rationale: str


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class SuggestionService:
    """Draft suggestions from profile data using an injected LLM client."""

    def __init__(self, client: LLMClient) -> None:
        """Initialise with an LLM client (real or fake)."""
        self._client = client

    def suggest_column_mappings(
        self, profile_columns: list[dict[str, Any]], canonical_fields: list[str]
    ) -> list[MappingSuggestion]:
        """Suggest canonical fields for the profiled columns (P5-2)."""
        system, user = mapping_prompt(profile_columns, canonical_fields)
        data = parse_json_response(self._client.complete(system=system, user=user))
        items = data.get("suggestions", []) if isinstance(data, dict) else data
        suggestions: list[MappingSuggestion] = []
        for item in items if isinstance(items, list) else []:
            source = item.get("source_column")
            field = item.get("canonical_field")
            if source and field:
                suggestions.append(
                    MappingSuggestion(
                        source_column=str(source),
                        canonical_field=str(field),
                        confidence=_as_float(item.get("confidence")),
                        rationale=str(item.get("rationale", "")),
                    )
                )
        return suggestions

    def suggest_taxonomy_term(self, raw_values: list[str], terms: list[str]) -> TaxonomySuggestion:
        """Suggest the canonical term to collapse raw values into (P5-3)."""
        system, user = taxonomy_prompt(raw_values, terms)
        data = parse_json_response(self._client.complete(system=system, user=user))
        payload = data if isinstance(data, dict) else {}
        return TaxonomySuggestion(
            canonical_term=str(payload.get("canonical_term", "")),
            confidence=_as_float(payload.get("confidence")),
            rationale=str(payload.get("rationale", "")),
        )

    def explain_anomaly(self, description: str, context: dict[str, Any] | None = None) -> str:
        """Return a plain-language likely-cause explanation for a flag (P5-5)."""
        system, user = anomaly_prompt(description, context)
        data = parse_json_response(self._client.complete(system=system, user=user))
        payload = data if isinstance(data, dict) else {}
        return str(payload.get("explanation", ""))
