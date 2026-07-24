"""Cross-source harmonization (Phase 16.2, config-as-data).

Unifies multiple Silver outputs into one panel: semantic field mapping (source
``link_clicks`` -> canonical ``clicks``) and taxonomy/value harmonization
(Meta "FB" / Google "Facebook" -> canonical ``meta``). Deterministic and
previewable; distinct from Stage-1 per-source column mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mmm_os.canonical.models import Taxonomies
from mmm_os.transform.types import Table


@dataclass(frozen=True)
class HarmonizationSpec:
    """A versioned-as-data cross-source harmonization spec.

    Attributes:
        field_map: source field name -> canonical field name (semantic mapping).
        value_map: field -> {raw value -> canonical value} (taxonomy harmonization).
    """

    field_map: dict[str, str] = field(default_factory=dict)
    value_map: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> HarmonizationSpec:
        """Build a spec from a plain dict (request payload / stored config)."""
        raw = raw or {}
        return cls(
            field_map={str(k): str(v) for k, v in (raw.get("field_map") or {}).items()},
            value_map={
                str(f): {str(k): str(v) for k, v in (m or {}).items()}
                for f, m in (raw.get("value_map") or {}).items()
            },
        )


def harmonize_rows(rows: Table, spec: HarmonizationSpec) -> Table:
    """Apply field renames + value remaps to a source's rows (pure)."""
    out: Table = []
    for row in rows:
        harmonized: dict[str, object] = {}
        for key, value in row.items():
            target = spec.field_map.get(key, key)
            mapped = value
            remap = spec.value_map.get(target)
            if remap is not None and isinstance(value, str) and value in remap:
                mapped = remap[value]
            harmonized[target] = mapped
        out.append(harmonized)
    return out


def suggest_harmonization(
    rows: Table, taxonomies: Taxonomies, *, field: str = "channel", taxonomy: str = "channel"
) -> list[dict[str, str]]:
    """Propose value harmonizations for a field, deterministic-first (Phase 16.3).

    For each distinct raw value of ``field`` that is not already a canonical term,
    resolve it against the taxonomy's aliases (deterministic). Values that resolve
    are returned as suggestions ``{raw, canonical}`` for human ratification (CC-5);
    unresolved values are left for the LLM assist (deferred).
    """
    tax = taxonomies.taxonomies.get(taxonomy)
    if tax is None:
        return []
    terms = set(tax.terms)
    seen: set[str] = set()
    suggestions: list[dict[str, str]] = []
    for row in rows:
        raw = row.get(field)
        if not isinstance(raw, str) or raw in terms or raw in seen:
            continue
        seen.add(raw)
        canonical = taxonomies.resolve(taxonomy, raw)
        if canonical is not None and canonical != raw:
            suggestions.append({"raw": raw, "canonical": canonical})
    return suggestions
