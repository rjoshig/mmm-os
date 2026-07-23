"""Prompt builders and response parsing for AI suggestions (P5-1).

Prompts are fed **profile data** (distinct values + column stats), never raw row
dumps. Responses are expected as strict JSON; ``parse_json_response`` tolerates
markdown code fences.
"""

from __future__ import annotations

import json
from typing import Any

from mmm_os.ai.errors import LLMResponseError

_MAPPING_SYSTEM = (
    "You map messy marketing-data columns to a fixed canonical schema. "
    "Respond with ONLY a JSON array; each element is "
    '{"source_column": str, "canonical_field": str, "confidence": number 0-1, '
    '"rationale": str}. Use the exact canonical field names provided, or omit a '
    "column you cannot confidently map."
)
_TAXONOMY_SYSTEM = (
    "You harmonise raw values to a controlled vocabulary. Respond with ONLY a JSON "
    'object {"canonical_term": str, "confidence": number 0-1, "rationale": str}.'
)
_ANOMALY_SYSTEM = (
    "You explain data-quality anomalies in one plain-language sentence. Respond "
    'with ONLY a JSON object {"explanation": str}.'
)
_TRANSFORM_SYSTEM = (
    "You are a marketing-data cleaning assistant. Given canonical-keyed column "
    "profiles and (optionally) open data-quality issues, propose declarative "
    "transform rules that clean or fix the data. Use ONLY these operations: "
    "normalize_text, map_value, fill_missing, cast_type, parse_date, "
    "convert_currency, dedupe. Respond with ONLY a JSON array; each element is "
    '{"target_field": str, "operation": str, "params": object, '
    '"confidence": number 0-1, "rationale": str}. Propose only rules you are '
    "confident about; return [] if the data looks clean."
)


def transform_prompt(
    profile_columns: list[dict[str, Any]],
    canonical_fields: list[str],
    issues: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """Build the (system, user) prompt for transform-rule suggestions (Cycle 4).

    ``issues`` (optional) are open validation findings (check + field) so the model
    can propose *remediation* rules, not just profile-driven cleaning.
    """
    user = json.dumps(
        {
            "canonical_fields": canonical_fields,
            "columns": profile_columns,
            "issues": issues or [],
        },
        ensure_ascii=False,
    )
    return _TRANSFORM_SYSTEM, user


def mapping_prompt(
    profile_columns: list[dict[str, Any]], canonical_fields: list[str]
) -> tuple[str, str]:
    """Build the (system, user) prompt for column-mapping suggestions."""
    user = json.dumps(
        {"canonical_fields": canonical_fields, "columns": profile_columns},
        ensure_ascii=False,
    )
    return _MAPPING_SYSTEM, user


def taxonomy_prompt(raw_values: list[str], terms: list[str]) -> tuple[str, str]:
    """Build the (system, user) prompt for a taxonomy-term suggestion."""
    user = json.dumps({"terms": terms, "raw_values": raw_values}, ensure_ascii=False)
    return _TAXONOMY_SYSTEM, user


def anomaly_prompt(description: str, context: dict[str, Any] | None = None) -> tuple[str, str]:
    """Build the (system, user) prompt for an anomaly explanation."""
    user = json.dumps({"flag": description, "context": context or {}}, ensure_ascii=False)
    return _ANOMALY_SYSTEM, user


def parse_json_response(text: str) -> Any:
    """Parse a model response as JSON, tolerating markdown code fences.

    Args:
        text: The raw model output.

    Returns:
        The parsed JSON value.

    Raises:
        LLMResponseError: If the text is not valid JSON.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"model did not return valid JSON: {exc}") from exc
