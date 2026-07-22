"""Structural transformation operations (03.1).

Registered handlers for ``rename_column``, ``cast_type``, ``normalize_text``,
``fill_missing`` (row-level, condition-aware) and ``dedupe`` (table-level).
"""

from __future__ import annotations

import re

from mmm_os.ingestion.structure import parse_number
from mmm_os.transform.conditions import matches
from mmm_os.transform.registry import RuleContext, TransformError, register
from mmm_os.transform.types import RuleSpec, Table

_WS = re.compile(r"\s+")
_TRUE = {"true", "yes", "1"}
_FALSE = {"false", "no", "0"}


@register("rename_column")
def rename_column(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Rename ``target_field`` to ``params['to']`` in every row."""
    to = rule.params.get("to")
    if not to:
        raise TransformError("rename_column requires params.to")
    for row in table:
        if rule.target_field in row:
            row[to] = row.pop(rule.target_field)
    return table


@register("cast_type")
def cast_type(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Cast ``target_field`` to ``params['to']`` (number/string/boolean)."""
    to = rule.params.get("to")
    for row in table:
        if not matches(row, rule.condition):
            continue
        value = row.get(rule.target_field)
        if value is None:
            continue
        row[rule.target_field] = _cast_value(str(value), to)
    return table


def _cast_value(value: str, to: str | None) -> object:
    if to == "number":
        return parse_number(value)
    if to == "boolean":
        low = value.strip().casefold()
        if low in _TRUE:
            return True
        if low in _FALSE:
            return False
        return None
    if to == "string":
        return value
    raise TransformError(f"cast_type: unsupported target type {to!r}")


@register("normalize_text")
def normalize_text(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Trim / case-normalise / collapse whitespace on ``target_field``."""
    params = rule.params
    for row in table:
        if not matches(row, rule.condition):
            continue
        value = row.get(rule.target_field)
        if value is None:
            continue
        text = str(value)
        if params.get("strip", True):
            text = text.strip()
        if params.get("collapse_ws"):
            text = _WS.sub(" ", text)
        if params.get("lower"):
            text = text.lower()
        elif params.get("upper"):
            text = text.upper()
        row[rule.target_field] = text
    return table


@register("fill_missing")
def fill_missing(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Fill null/empty ``target_field`` with ``params['value']``."""
    fill = rule.params.get("value")
    for row in table:
        if not matches(row, rule.condition):
            continue
        current = row.get(rule.target_field)
        if current is None or current == "":
            row[rule.target_field] = fill
    return table


@register("dedupe")
def dedupe(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Remove duplicate rows, keeping the first occurrence.

    ``params['keys']`` (optional) dedupes by those fields; otherwise by the whole row.
    """
    keys = rule.params.get("keys")
    seen: set[tuple[object, ...]] = set()
    result: Table = []
    for row in table:
        if keys:
            signature = tuple(row.get(k) for k in keys)
        else:
            signature = tuple(sorted(row.items()))
        if signature in seen:
            continue
        seen.add(signature)
        result.append(row)
    return result
