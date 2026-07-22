"""Value/domain transformation operations (03.2).

Registered handlers for ``map_value`` (taxonomy harmonisation, P3-6),
``parse_date``, ``convert_currency`` (row-level) and ``reshape`` (wide→long,
table-level, OQ-3.2).
"""

from __future__ import annotations

from datetime import datetime

from mmm_os.ingestion.structure import match_date, parse_number
from mmm_os.transform.conditions import matches
from mmm_os.transform.registry import RuleContext, TransformError, register
from mmm_os.transform.types import RuleSpec, Table


@register("map_value")
def map_value(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Collapse raw values on ``target_field`` to canonical terms.

    ``params`` supports an explicit ``mapping`` (raw → canonical) and/or a
    ``taxonomy`` name resolved via the loaded taxonomies. Unmatched values fall
    back to ``default`` if given, else are kept as-is unless ``keep_unmatched``
    is false (then set to ``None``).
    """
    mapping: dict[str, str] = rule.params.get("mapping", {})
    taxonomy = rule.params.get("taxonomy")
    default = rule.params.get("default")
    keep_unmatched = rule.params.get("keep_unmatched", True)

    for row in table:
        if not matches(row, rule.condition):
            continue
        value = row.get(rule.target_field)
        if value is None:
            continue
        raw = str(value)
        resolved: str | None = mapping.get(raw)
        if resolved is None and taxonomy and ctx.taxonomies is not None:
            resolved = ctx.taxonomies.resolve(taxonomy, raw)
        if resolved is not None:
            row[rule.target_field] = resolved
        elif default is not None:
            row[rule.target_field] = default
        elif not keep_unmatched:
            row[rule.target_field] = None
    return table


@register("parse_date")
def parse_date(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Parse ``target_field`` to a normalised date string.

    ``params.output`` sets the output format (default ISO ``%Y-%m-%d``);
    ``params.formats`` optionally restricts the input formats tried.
    """
    output = rule.params.get("output", "%Y-%m-%d")
    formats: list[str] | None = rule.params.get("formats")
    for row in table:
        if not matches(row, rule.condition):
            continue
        value = row.get(rule.target_field)
        if value is None:
            continue
        text = str(value)
        fmt = _match_with(text, formats) if formats else match_date(text)
        if fmt is not None:
            row[rule.target_field] = datetime.strptime(text, fmt).strftime(output)
    return table


def _match_with(value: str, formats: list[str]) -> str | None:
    for fmt in formats:
        try:
            datetime.strptime(value, fmt)
        except ValueError:
            continue
        return fmt
    return None


@register("convert_currency")
def convert_currency(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Multiply a numeric ``target_field`` by a conversion rate.

    ``params.rate`` applies a fixed multiplier; alternatively ``params.rates``
    (a ``{currency: rate}`` map) with ``params.currency_field`` looks the rate up
    per row.
    """
    fixed = rule.params.get("rate")
    rates: dict[str, float] = rule.params.get("rates", {})
    currency_field = rule.params.get("currency_field")

    for row in table:
        if not matches(row, rule.condition):
            continue
        value = row.get(rule.target_field)
        if value is None:
            continue
        number = parse_number(str(value)) if isinstance(value, str) else float(value)
        if number is None:
            continue
        rate = fixed
        if rate is None and currency_field is not None:
            rate = rates.get(str(row.get(currency_field)))
        if rate is None:
            raise TransformError("convert_currency requires a rate or matching rates entry")
        row[rule.target_field] = number * float(rate)
    return table


@register("reshape")
def reshape(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Reshape wide → long (OQ-3.2).

    ``params``: ``id_vars`` (kept per output row), ``value_vars`` (columns to
    unpivot), ``var_name`` (target dimension holding the source column name), and
    ``value_name`` (target measure holding the cell value).
    """
    id_vars: list[str] = rule.params.get("id_vars", [])
    value_vars: list[str] = rule.params.get("value_vars", [])
    var_name = rule.params.get("var_name")
    value_name = rule.params.get("value_name")
    if not value_vars or not var_name or not value_name:
        raise TransformError("reshape requires value_vars, var_name, and value_name")

    result: Table = []
    for row in table:
        base = {key: row.get(key) for key in id_vars}
        for column in value_vars:
            if column not in row:
                continue
            new_row = dict(base)
            new_row[var_name] = column
            new_row[value_name] = row.get(column)
            result.append(new_row)
    return result
