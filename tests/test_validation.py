"""Unit tests for the validation engine, checks, and anomaly detection (04.1/04.2)."""

from __future__ import annotations

from mmm_os.canonical import load_canonical_schema
from mmm_os.validation.anomaly import detect_anomalies
from mmm_os.validation.engine import validate
from mmm_os.validation.policy import Policy, is_blocked


def _flags_by_check(flags: list) -> dict[str, list]:
    out: dict[str, list] = {}
    for flag in flags:
        out.setdefault(flag.check, []).append(flag)
    return out


def test_missing_required_is_blocking() -> None:
    """A missing required field is a blocking flag."""
    schema = load_canonical_schema()
    flags = validate([{"date": "2026-01-01", "spend": "100"}], schema)  # no channel
    by_check = _flags_by_check(flags)
    assert "missing_required" in by_check
    assert is_blocked(flags)


def test_factor_only_row_satisfies_meaningful_requirement() -> None:
    """A factor row (date + channel + a factor, no media measure) is not flagged.

    Factor sources (price/holiday/weather series) carry no spend/impressions, so a
    factor value satisfies the "meaningful row" rule instead of a measure (Cycle 2).
    """
    schema = load_canonical_schema()
    flags = validate(
        [{"date": "2026-01-01", "channel": "Facebook", "price_index": "1.05"}], schema
    )
    by_check = _flags_by_check(flags)
    assert "missing_required" not in by_check
    assert not is_blocked(flags)


def test_row_with_neither_measure_nor_factor_is_blocking() -> None:
    """A row with a required dimension but no measure and no factor is still flagged."""
    schema = load_canonical_schema()
    flags = validate([{"date": "2026-01-01", "channel": "Facebook"}], schema)
    by_check = _flags_by_check(flags)
    assert "missing_required" in by_check
    assert is_blocked(flags)


def test_zero_spend_day_is_informational() -> None:
    """A dated row with zero or blank spend is flagged (info, not blocking)."""
    schema = load_canonical_schema()
    rows = [
        {"date": "2026-01-01", "channel": "Facebook", "spend": "100"},
        {"date": "2026-01-02", "channel": "Facebook", "spend": "0"},  # explicit zero
        # blank spend but impressions present (real activity):
        {"date": "2026-01-03", "channel": "Facebook", "spend": "", "impressions": "500"},
    ]
    flags = validate(rows, schema)
    by_check = _flags_by_check(flags)
    assert "zero_spend" in by_check
    assert len(by_check["zero_spend"]) == 2
    assert "missing_required" not in by_check  # no double-flag with the blank row
    assert not is_blocked(flags)  # informational only


def test_date_gap_is_grain_aware_for_weekly_series() -> None:
    """A weekly series flags only gaps larger than a week, not every 7-day step."""
    schema = load_canonical_schema()
    # Weekly Mondays with one missing week (Jan 19 skipped).
    rows = [
        {"date": "2026-01-05", "channel": "Facebook", "spend": "10"},
        {"date": "2026-01-12", "channel": "Facebook", "spend": "10"},
        {"date": "2026-01-26", "channel": "Facebook", "spend": "10"},  # gap: skips Jan 19
    ]
    flags = validate(rows, schema)
    gaps = _flags_by_check(flags).get("date_gap", [])
    assert len(gaps) == 1  # only the true >1-week gap, not the normal weekly steps
    assert gaps[0].location["from"] == "2026-01-12"


def test_negative_measure_is_blocking() -> None:
    """A negative measure is flagged blocking."""
    schema = load_canonical_schema()
    flags = validate([{"date": "2026-01-01", "channel": "Facebook", "spend": "-5"}], schema)
    by_check = _flags_by_check(flags)
    assert "negative_measure" in by_check
    assert is_blocked(flags)


def test_duplicate_and_type_mismatch_are_warnings() -> None:
    """Duplicate rows and non-numeric measures are warnings (not blocking)."""
    schema = load_canonical_schema()
    rows = [
        {"date": "2026-01-01", "channel": "Facebook", "spend": "abc"},
        {"date": "2026-01-01", "channel": "Facebook", "spend": "abc"},
    ]
    flags = validate(rows, schema)
    by_check = _flags_by_check(flags)
    assert "duplicate_row" in by_check
    assert "type_mismatch" in by_check


def test_policy_overrides_severity() -> None:
    """A policy override changes a check's severity."""
    schema = load_canonical_schema()
    rows = [{"date": "2026-01-01", "channel": "Facebook", "spend": "abc"}]
    flags = validate(rows, schema, Policy({"type_mismatch": "blocking"}))
    assert is_blocked(flags)


def test_date_gap_detected() -> None:
    """A missing day in a daily sequence is flagged."""
    schema = load_canonical_schema()
    rows = [
        {"date": "2026-01-01", "channel": "Facebook", "spend": "1"},
        {"date": "2026-01-03", "channel": "Facebook", "spend": "1"},  # gap: 2026-01-02 missing
    ]
    flags = validate(rows, schema)
    assert "date_gap" in _flags_by_check(flags)


def test_anomaly_detects_spike() -> None:
    """A large one-off spike is detected as an outlier."""
    rows = [{"spend": v} for v in ["100", "110", "105", "95", "500"]]  # 500 is the spike
    findings = detect_anomalies(rows, "spend")
    assert any(f.location["row"] == 4 for f in findings)
