"""Rule-based validation checks (P4-1).

Pure functions over canonical-keyed records; each returns ``Finding`` objects
(severity is assigned later by the policy). Records are expected to be mapped +
transformed (dates normalised to ISO, measures numeric where possible).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from mmm_os.canonical.models import CanonicalSchema
from mmm_os.ingestion.structure import match_date, parse_number
from mmm_os.transform.types import Table
from mmm_os.validation.flags import Finding

_ISO = "%Y-%m-%d"


def _is_empty(value: object) -> bool:
    return value is None or value == ""


def _to_number(value: object) -> float | None:
    """Coerce a cell value to a float, or ``None`` if not numeric."""
    if isinstance(value, str):
        return parse_number(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def check_missing_required(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag rows missing a required dimension, or with neither enough measures nor a factor.

    A row is meaningful with at least ``min_required`` measures OR at least one
    factor value (factor sources — price/holiday/weather series — carry no media
    measures), per the Cycle-2 measure-or-factor policy.
    """
    required = [f.name for f in schema.dimensions if f.required]
    measures = {f.name for f in schema.measures}
    factors = schema.factor_names()
    min_required = schema.measure_policy.min_required
    findings: list[Finding] = []
    for i, row in enumerate(table):
        for field_name in required:
            if _is_empty(row.get(field_name)):
                findings.append(
                    Finding(
                        "missing_required",
                        f"missing required field {field_name!r}",
                        {"row": i, "field": field_name},
                    )
                )
        present_measures = [m for m in measures if not _is_empty(row.get(m))]
        has_factor = any(not _is_empty(row.get(f)) for f in factors)
        if len(present_measures) < min_required and not has_factor:
            findings.append(
                Finding(
                    "missing_required",
                    f"row has fewer than {min_required} measure(s) and no factor value",
                    {"row": i},
                )
            )
    return findings


def check_type_mismatches(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag non-numeric measures and unparseable required dates."""
    measures = {f.name for f in schema.measures}
    findings: list[Finding] = []
    for i, row in enumerate(table):
        for measure in measures:
            value = row.get(measure)
            if _is_empty(value):
                continue
            if isinstance(value, str) and parse_number(value) is None:
                findings.append(
                    Finding(
                        "type_mismatch", f"{measure} is not numeric", {"row": i, "field": measure}
                    )
                )
        date_value = row.get("date")
        if (
            not _is_empty(date_value)
            and isinstance(date_value, str)
            and match_date(date_value) is None
        ):
            findings.append(
                Finding(
                    "type_mismatch_required",
                    "date is not a valid date",
                    {"row": i, "field": "date"},
                )
            )
    return findings


def check_negative_measures(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag negative measure values (e.g. negative spend)."""
    measures = {f.name for f in schema.measures}
    findings: list[Finding] = []
    for i, row in enumerate(table):
        for measure in measures:
            value = row.get(measure)
            if _is_empty(value):
                continue
            number = _to_number(value)
            if number is not None and number < 0:
                findings.append(
                    Finding(
                        "negative_measure",
                        f"{measure} is negative ({number})",
                        {"row": i, "field": measure},
                    )
                )
    return findings


def check_duplicate_rows(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag rows that are exact duplicates of an earlier row."""
    seen: set[tuple[tuple[str, object], ...]] = set()
    findings: list[Finding] = []
    for i, row in enumerate(table):
        signature = tuple(sorted(row.items()))
        if signature in seen:
            findings.append(Finding("duplicate_row", "duplicate row", {"row": i}))
        else:
            seen.add(signature)
    return findings


def _expected_step_days(unique: list[datetime]) -> int:
    """Infer a series' expected period step (days) from its modal spacing.

    Returns 7 for a weekly series, 31 for monthly, else 1 (daily / unknown) — so the
    continuity check adapts to the grain instead of assuming daily (Cycle 2).
    """
    if len(unique) < 2:
        return 1
    diffs = [(later - earlier).days for earlier, later in zip(unique, unique[1:], strict=False)]
    modal = Counter(diffs).most_common(1)[0][0]
    if modal == 7:
        return 7
    if 28 <= modal <= 31:
        return 31
    return 1


def check_date_gaps(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag breaks in the date series, adapting to its grain (daily/weekly/monthly).

    The expected period step is inferred from the modal spacing (Cycle 2), so a
    weekly series flags gaps larger than a week and a monthly series larger than a
    month — not every non-daily step.
    """
    dates: list[datetime] = []
    for row in table:
        value = row.get("date")
        if isinstance(value, str) and match_date(value) == _ISO:
            dates.append(datetime.strptime(value, _ISO))
    unique = sorted(set(dates))
    step = _expected_step_days(unique)
    findings: list[Finding] = []
    for earlier, later in zip(unique, unique[1:], strict=False):
        if (later - earlier).days > step:
            findings.append(
                Finding(
                    "date_gap",
                    f"gap between {earlier.date()} and {later.date()}",
                    {"from": earlier.strftime(_ISO), "to": later.strftime(_ISO)},
                )
            )
    return findings


def check_zero_spend_days(table: Table, schema: CanonicalSchema) -> list[Finding]:
    """Flag dated rows whose ``spend`` measure is zero or blank (Cycle 2).

    A zero-/missing-spend period in an otherwise active series is a data-quality
    heads-up for MMM (often legitimate, sometimes a data drop) — informational, not
    blocking. Only runs when ``spend`` is a canonical measure and present on the row.
    """
    measures = {f.name for f in schema.measures}
    if "spend" not in measures:
        return []
    other_measures = measures - {"spend"}
    findings: list[Finding] = []
    for i, row in enumerate(table):
        if "spend" not in row or _is_empty(row.get("date")):
            continue
        value = row.get("spend")
        number = _to_number(value)
        is_zero = number is not None and number == 0
        # Blank spend is only a zero-spend signal when the row *has* other activity;
        # a wholly measure-less row is left to check_missing_required (blocking),
        # so the two checks never double-flag the same row.
        blank_with_activity = _is_empty(value) and any(
            not _is_empty(row.get(m)) for m in other_measures
        )
        if is_zero or blank_with_activity:
            findings.append(
                Finding(
                    "zero_spend",
                    "zero or missing spend for the period",
                    {"row": i, "field": "spend"},
                )
            )
    return findings


ALL_CHECKS = (
    check_missing_required,
    check_type_mismatches,
    check_negative_measures,
    check_duplicate_rows,
    check_date_gaps,
    check_zero_spend_days,
)
