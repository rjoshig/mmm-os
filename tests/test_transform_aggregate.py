"""Unit tests for the time-grain aggregate operation (Cycle 2, Slice 2)."""

from __future__ import annotations

from mmm_os.canonical import load_canonical_schema
from mmm_os.transform.engine import apply_rules
from mmm_os.transform.registry import RuleContext
from mmm_os.transform.types import RuleSpec


def _ctx() -> RuleContext:
    return RuleContext(schema=load_canonical_schema())


def test_weekly_aggregate_sums_measures_and_groups_by_channel() -> None:
    """Daily rows roll up to one weekly row per channel, summing measures."""
    # Mon 2026-01-05 .. Wed 2026-01-07, two channels.
    table = [
        {"date": "2026-01-05", "channel": "Facebook", "spend": "100", "clicks": "10"},
        {"date": "2026-01-06", "channel": "Facebook", "spend": "50", "clicks": "5"},
        {"date": "2026-01-07", "channel": "Google", "spend": "30", "clicks": "3"},
    ]
    rules = [RuleSpec(target_field="", operation="aggregate", params={"freq": "weekly"})]
    out = apply_rules(table, rules, _ctx())

    fb = [r for r in out if r["channel"] == "Facebook"]
    assert len(fb) == 1
    assert fb[0]["date"] == "2026-01-05"  # Monday week-start
    assert fb[0]["spend"] == 150.0
    assert fb[0]["clicks"] == 15.0
    goog = [r for r in out if r["channel"] == "Google"]
    assert goog[0]["spend"] == 30.0


def test_weekly_aggregate_averages_numeric_factors() -> None:
    """Numeric factors (e.g. price_index) are averaged, not summed."""
    table = [
        {"date": "2026-01-05", "channel": "Facebook", "spend": "100", "price_index": "1.0"},
        {"date": "2026-01-06", "channel": "Facebook", "spend": "100", "price_index": "2.0"},
    ]
    rules = [RuleSpec(target_field="", operation="aggregate", params={})]
    out = apply_rules(table, rules, _ctx())
    assert len(out) == 1
    assert out[0]["spend"] == 200.0
    assert out[0]["price_index"] == 1.5


def test_weekly_aggregate_fills_date_gaps_with_zero_measures() -> None:
    """A missing week is inserted (continuous series) with zero-filled measures."""
    table = [
        {"date": "2026-01-05", "channel": "Facebook", "spend": "100"},  # week of Jan 5
        {"date": "2026-01-19", "channel": "Facebook", "spend": "200"},  # week of Jan 19 (gap Jan12)
    ]
    rules = [RuleSpec(target_field="", operation="aggregate", params={"freq": "weekly"})]
    out = apply_rules(table, rules, _ctx())
    by_date = {r["date"]: r for r in out}
    assert set(by_date) == {"2026-01-05", "2026-01-12", "2026-01-19"}
    assert by_date["2026-01-12"]["spend"] == 0.0
    assert by_date["2026-01-12"]["channel"] == "Facebook"


def test_aggregate_is_idempotent() -> None:
    """Re-running aggregate on its own output is stable (CC-6)."""
    table = [
        {"date": "2026-01-05", "channel": "Facebook", "spend": "100"},
        {"date": "2026-01-06", "channel": "Facebook", "spend": "50"},
    ]
    rules = [RuleSpec(target_field="", operation="aggregate", params={})]
    once = apply_rules(table, rules, _ctx())
    twice = apply_rules(once, rules, _ctx())
    assert once == twice


def test_monthly_aggregate_buckets_to_first_of_month() -> None:
    """Monthly frequency buckets rows to the first of the month."""
    table = [
        {"date": "2026-01-05", "channel": "Facebook", "spend": "100"},
        {"date": "2026-01-28", "channel": "Facebook", "spend": "100"},
    ]
    rules = [RuleSpec(target_field="", operation="aggregate", params={"freq": "monthly"})]
    out = apply_rules(table, rules, _ctx())
    assert len(out) == 1
    assert out[0]["date"] == "2026-01-01"
    assert out[0]["spend"] == 200.0


def test_aggregate_explicit_fields_without_schema() -> None:
    """Explicit sum/group_by params work without a schema in context."""
    table = [
        {"week": "2026-01-05", "geo": "US", "revenue": "10"},
        {"week": "2026-01-06", "geo": "US", "revenue": "20"},
    ]
    rules = [
        RuleSpec(
            target_field="",
            operation="aggregate",
            params={"date_field": "week", "group_by": ["geo"], "sum": ["revenue"]},
        )
    ]
    out = apply_rules(table, rules, RuleContext())
    assert len(out) == 1
    assert out[0]["week"] == "2026-01-05"
    assert out[0]["revenue"] == 30.0
