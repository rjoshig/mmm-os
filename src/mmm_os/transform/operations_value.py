"""Value/domain transformation operations (03.2).

Registered handlers for ``map_value`` (taxonomy harmonisation, P3-6),
``parse_date``, ``convert_currency`` (row-level) and ``reshape`` (wide→long,
table-level, OQ-3.2).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

    Three ways to resolve the rate, in precedence order:
      - ``params.rate`` — a fixed multiplier.
      - ``params.rates`` (a ``{currency: rate}`` map) with ``params.currency_field``
        — look the rate up per row from the source currency.
      - ``params.to_reporting`` (``True``) with ``params.currency_field`` — normalize
        each row's value into the tenant **reporting currency** using the reporting
        FX table in context (``ctx.reporting``); a row already in the reporting
        currency is unchanged (rate 1.0). This is the end-to-end normalization path.
    """
    fixed = rule.params.get("rate")
    rates: dict[str, float] = rule.params.get("rates", {})
    currency_field = rule.params.get("currency_field")
    to_reporting = bool(rule.params.get("to_reporting", False))

    for row in table:
        if not matches(row, rule.condition):
            continue
        value = row.get(rule.target_field)
        if value is None:
            continue
        number = parse_number(str(value)) if isinstance(value, str) else float(value)
        if number is None:
            continue
        rate = _resolve_rate(row, fixed, rates, currency_field, to_reporting, ctx)
        if rate is None:
            raise TransformError(
                "convert_currency: no rate — provide rate/rates, or to_reporting with "
                "a reporting FX table covering the row's currency"
            )
        row[rule.target_field] = number * float(rate)
    return table


def _resolve_rate(
    row: dict[str, object],
    fixed: object,
    rates: dict[str, float],
    currency_field: str | None,
    to_reporting: bool,
    ctx: RuleContext,
) -> float | None:
    """Resolve the FX multiplier for one row (fixed > rates map > reporting frame)."""
    if fixed is not None:
        return float(fixed)  # type: ignore[arg-type]
    if currency_field is None:
        return None
    source_currency = str(row.get(currency_field))
    if rates:
        found = rates.get(source_currency)
        if found is not None:
            return float(found)
    if to_reporting and ctx.reporting is not None:
        return ctx.reporting.rate_to_reporting(source_currency)
    return None


@register("normalize_timezone")
def normalize_timezone(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Convert a timestamp ``target_field`` to a single reporting timezone.

    ``params``:
      - ``from_tz``: the source timezone (IANA name, e.g. ``America/New_York``);
        defaults to ``UTC``.
      - ``to_tz``: the target timezone; defaults to the reporting timezone in
        context (``ctx.reporting.timezone``) or ``UTC``.
      - ``to_date`` (``True``): also write the timezone-normalized calendar date to
        ``params.date_field`` (default ``date``) — so daily buckets are assigned in
        the reporting frame, not the source's.

    Rows whose ``target_field`` is empty or unparseable are left unchanged.
    """
    from_tz = _zone(str(rule.params.get("from_tz", "UTC")))
    default_to = ctx.reporting.timezone if ctx.reporting is not None else "UTC"
    to_tz = _zone(str(rule.params.get("to_tz", default_to)))
    to_date = bool(rule.params.get("to_date", False))
    date_field = str(rule.params.get("date_field", "date"))

    for row in table:
        if not matches(row, rule.condition):
            continue
        raw = row.get(rule.target_field)
        moment = _parse_datetime(raw)
        if moment is None:
            continue
        localized = moment.replace(tzinfo=from_tz) if moment.tzinfo is None else moment
        converted = localized.astimezone(to_tz)
        row[rule.target_field] = converted.isoformat()
        if to_date:
            row[date_field] = converted.strftime("%Y-%m-%d")
    return table


def _zone(name: str) -> ZoneInfo:
    """Resolve an IANA timezone name, raising a clear error for a bad name."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TransformError(f"normalize_timezone: unknown timezone {name!r}") from exc


def _parse_datetime(value: object) -> datetime | None:
    """Parse a timestamp/date value into a ``datetime``, or ``None``."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    fmt = match_date(text)
    if fmt is None:
        return None
    try:
        return datetime.strptime(text, fmt)
    except ValueError:
        return None


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
