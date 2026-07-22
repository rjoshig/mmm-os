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
