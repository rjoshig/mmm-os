"""Time-grain aggregation (Cycle 2): roll a table up to a coarser date grain.

MMM's standard modelling grain is **weekly** — spend/impressions summed per week,
factors averaged, dimensions preserved, and the date series made continuous
(adstock-ready). ``aggregate`` rolls daily (or finer) rows up to weekly or monthly
periods.

Fields are classified either explicitly (``sum`` / ``mean`` / ``group_by`` params)
or, when those are omitted and a canonical schema is in context, automatically:
measures → summed, numeric factors → averaged, dimensions → grouping keys. Any other
column carries its first value in the group. The result is sorted by (group keys,
period) so re-running is deterministic (CC-6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from mmm_os.canonical.models import CanonicalSchema, FieldType
from mmm_os.ingestion.structure import match_date, parse_number
from mmm_os.transform.registry import RuleContext, TransformError, register
from mmm_os.transform.types import RuleSpec, Table

_ISO = "%Y-%m-%d"
_WEEKDAY_OFFSET = {"monday": 0, "sunday": 6}


@dataclass
class _Bucket:
    """Accumulator for one (period, group-key) cell."""

    period: datetime
    sums: dict[str, float] = field(default_factory=dict)
    means: dict[str, list[float]] = field(default_factory=dict)
    first: dict[str, object] = field(default_factory=dict)


def _parse_date(value: object) -> datetime | None:
    """Parse a cell value into a ``datetime``, or ``None`` if it is not a date."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    fmt = match_date(value)
    if fmt is None:
        return None
    try:
        return datetime.strptime(value, fmt)
    except ValueError:
        return None


def _period_start(when: datetime, freq: str, week_start: str) -> datetime:
    """Return the period-start date for ``when`` at the given frequency."""
    if freq == "monthly":
        return datetime(when.year, when.month, 1)
    # weekly (default): snap back to the configured week-start weekday.
    start_weekday = _WEEKDAY_OFFSET.get(week_start, 0)
    delta = (when.weekday() - start_weekday) % 7
    day = datetime(when.year, when.month, when.day) - timedelta(days=delta)
    return day


def _next_period(start: datetime, freq: str) -> datetime:
    """Return the start of the period following ``start``."""
    if freq == "monthly":
        year, month = (start.year + 1, 1) if start.month == 12 else (start.year, start.month + 1)
        return datetime(year, month, 1)
    return start + timedelta(days=7)


def _to_number(value: object) -> float | None:
    """Coerce a value to a float, or ``None`` if it is not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return parse_number(value)
    return None


def _classify(
    schema: CanonicalSchema, keys: set[str], date_field: str
) -> tuple[list[str], list[str], list[str]]:
    """Split observed columns into (group_by, sum, mean) using the canonical schema.

    Measures are summed, numeric factors are averaged, and dimensions (except the
    date field) are grouping keys. Columns not in the schema — or non-numeric
    factors — are left for first-value carry.
    """
    measures = {f.name for f in schema.measures}
    dimensions = {f.name for f in schema.dimensions}
    numeric_factors = {f.name for f in schema.factors if f.type is FieldType.NUMBER}
    sum_fields = [k for k in keys if k in measures]
    mean_fields = [k for k in keys if k in numeric_factors]
    group_by = [k for k in keys if k in dimensions and k != date_field]
    return sorted(group_by), sorted(sum_fields), sorted(mean_fields)


@register("aggregate")
def aggregate(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Roll a table up to a coarser date grain (weekly/monthly).

    ``params``:
      - ``freq``: ``"weekly"`` (default) or ``"monthly"``.
      - ``week_start``: ``"monday"`` (default) or ``"sunday"`` (weekly only).
      - ``date_field``: the date column to bucket (default ``"date"``).
      - ``group_by`` / ``sum`` / ``mean``: explicit field lists; when omitted and a
        schema is in context they are inferred (dimensions / measures / numeric
        factors).
      - ``fill_gaps``: insert missing periods per group so the series is continuous
        (default ``True``); summed measures are zero-filled, other columns null.

    Rows whose ``date_field`` is missing or unparseable are dropped (they cannot be
    assigned to a period).
    """
    params = rule.params
    freq = str(params.get("freq", "weekly"))
    if freq not in ("weekly", "monthly"):
        raise TransformError(f"aggregate: unsupported freq {freq!r} (weekly|monthly)")
    week_start = str(params.get("week_start", "monday"))
    date_field = str(params.get("date_field", "date"))
    fill_gaps = bool(params.get("fill_gaps", True))

    keys = {k for row in table for k in row}
    group_by = params.get("group_by")
    sum_fields = params.get("sum")
    mean_fields = params.get("mean")
    if group_by is None and sum_fields is None and mean_fields is None:
        if ctx.schema is None:
            raise TransformError(
                "aggregate needs a canonical schema in context or explicit "
                "group_by/sum/mean params"
            )
        group_by, sum_fields, mean_fields = _classify(ctx.schema, keys, date_field)
    else:
        group_by = list(group_by or [])
        sum_fields = list(sum_fields or [])
        mean_fields = list(mean_fields or [])

    carry = sorted(keys - {date_field, *group_by, *sum_fields, *mean_fields})

    # Accumulate per (period, group-key) bucket.
    buckets: dict[tuple[object, ...], _Bucket] = {}
    for row in table:
        when = _parse_date(row.get(date_field))
        if when is None:
            continue
        period = _period_start(when, freq, week_start)
        key = (period.strftime(_ISO), *(row.get(g) for g in group_by))
        acc = buckets.get(key)
        if acc is None:
            acc = _Bucket(period=period)
            buckets[key] = acc
        for name in sum_fields:
            number = _to_number(row.get(name))
            if number is not None:
                acc.sums[name] = acc.sums.get(name, 0.0) + number
        for name in mean_fields:
            number = _to_number(row.get(name))
            if number is not None:
                acc.means.setdefault(name, []).append(number)
        for name in carry:
            if name not in acc.first and row.get(name) not in (None, ""):
                acc.first[name] = row.get(name)

    result: Table = []
    for key, acc in buckets.items():
        group_values = dict(zip(group_by, key[1:], strict=True))
        result.append(_emit(str(key[0]), date_field, group_values, acc))

    if fill_gaps:
        result = _fill_gaps(result, group_by, sum_fields, freq, date_field)

    # Deterministic ordering (CC-6): by group keys then period.
    result.sort(key=lambda r: tuple(str(r.get(g, "")) for g in group_by) + (str(r[date_field]),))
    return result


def _emit(
    period_iso: str, date_field: str, group_values: dict[str, object], acc: _Bucket
) -> dict[str, object]:
    """Build one output row from an accumulator bucket."""
    out: dict[str, object] = {date_field: period_iso, **group_values}
    for name, total in acc.sums.items():
        out[name] = total
    for name, values in acc.means.items():
        out[name] = sum(values) / len(values) if values else None
    for name, value in acc.first.items():
        out[name] = value
    return out


def _fill_gaps(
    rows: Table, group_by: list[str], sum_fields: list[str], freq: str, date_field: str
) -> Table:
    """Insert missing periods per group so each group's series is continuous.

    Summed measures are zero-filled in inserted rows; other columns are left null.
    """
    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(tuple(row.get(g) for g in group_by), []).append(row)

    filled: Table = list(rows)
    for gkey, grows in groups.items():
        present = {str(r[date_field]) for r in grows}
        periods = sorted(datetime.strptime(str(r[date_field]), _ISO) for r in grows)
        cursor = periods[0]
        end = periods[-1]
        while cursor < end:
            cursor = _next_period(cursor, freq)
            iso = cursor.strftime(_ISO)
            if iso in present:
                continue
            gap_row: dict[str, object] = {date_field: iso}
            for name, value in zip(group_by, gkey, strict=True):
                gap_row[name] = value
            for measure in sum_fields:
                gap_row[measure] = 0.0
            filled.append(gap_row)
    return filled
