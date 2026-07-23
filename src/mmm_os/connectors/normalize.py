"""Template-driven normalization: partner report rows → canonical records (Phase 9).

Applies a connector's ``default_mapping.yaml`` ``column_map`` to raw report rows,
producing canonical-shaped records inside a :class:`~mmm_os.sources.landed.LandedDataset`.
Supports the ops the shipped templates use: ``__constant__`` / ``__account__`` /
null sources, ``parse_date``, ``map_value`` (taxonomy), ``extract_action`` (nested
Meta metrics), ``micros_to_currency`` (Google), ``cast_type`` (string→number,
TikTok), and ``resolve_geo_target`` (Google geo ids).
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from mmm_os.sources.landed import SOURCE_TYPE_API_CONNECTOR, LandedDataset, LandedTable

_PKG_ROOT = Path(__file__).parent
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y")


@lru_cache
def load_template(connector_key: str) -> dict[str, Any]:
    """Load and cache a connector's default mapping template."""
    path = _PKG_ROOT / connector_key / "templates" / "default_mapping.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def _extract_action(actions: Any, action_type: str | None) -> float | None:
    if not isinstance(actions, list):
        return None
    for item in actions:
        if isinstance(item, dict) and item.get("action_type") == action_type:
            return _to_number(item.get("value"))
    return None


def apply_column_map(
    row: dict[str, Any],
    column_map: dict[str, Any],
    taxonomies: dict[str, Any],
    *,
    account_ctx: dict[str, Any],
) -> dict[str, Any]:
    """Map one raw report row to a canonical record via the template's column_map."""
    out: dict[str, Any] = {}
    for field, spec in column_map.items():
        source = spec.get("source")
        op = spec.get("op")
        if source == "__constant__":
            out[field] = spec.get("value")
            continue
        if source == "__account__":
            out[field] = account_ctx.get(field)
            continue
        if source is None:
            out[field] = None
            continue
        raw = row.get(source)
        if op == "parse_date":
            out[field] = _parse_date(raw)
        elif op == "map_value":
            tax = taxonomies.get(spec.get("taxonomy", ""), {}) or {}
            out[field] = tax.get(str(raw), raw)
        elif op == "extract_action":
            out[field] = _extract_action(raw, spec.get("action_type"))
        elif op == "micros_to_currency":
            n = _to_number(raw)
            out[field] = n / 1_000_000 if n is not None else None
        elif op == "cast_type" and spec.get("to") == "number":
            out[field] = _to_number(raw)
        elif op == "resolve_geo_target":
            geo_map = account_ctx.get("geo_map", {})
            out[field] = geo_map.get(str(raw), raw)
        else:
            out[field] = raw
    return out


def normalize_rows(
    connector_key: str,
    rows: list[dict[str, Any]],
    *,
    account_ctx: dict[str, Any] | None = None,
    source_ref: dict[str, Any] | None = None,
) -> LandedDataset:
    """Normalize partner rows into a canonical-record ``LandedDataset``."""
    template = load_template(connector_key)
    column_map: dict[str, Any] = template.get("column_map", {})
    taxonomies: dict[str, Any] = template.get("taxonomies", {}) or {}
    ctx = account_ctx or {}
    records = [apply_column_map(r, column_map, taxonomies, account_ctx=ctx) for r in rows]
    columns = [
        {"index": i, "name": name, "type": "string", "date_format": None}
        for i, name in enumerate(column_map)
    ]
    table = LandedTable(
        name=connector_key, index=0, columns=columns, confident=True, records=records
    )
    return LandedDataset(
        source_type=SOURCE_TYPE_API_CONNECTOR, source_ref=source_ref or {}, tables=[table]
    )
