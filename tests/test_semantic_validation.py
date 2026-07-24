"""Tests for Phase 17 — semantic & output validation (CC-15)."""

from __future__ import annotations

from mmm_os.canonical import load_and_validate
from mmm_os.validation.engine import validate
from mmm_os.validation.semantic import (
    check_ctr_plausibility,
    check_funnel_monotonicity,
    check_revenue_conversion_coherence,
    check_spend_delivery_coherence,
)
from mmm_os.validation.stats import output_statistics

_SCHEMA = load_and_validate().schema


def test_funnel_monotonicity_flags_clicks_over_impressions() -> None:
    table = [{"clicks": 100, "impressions": 10}]
    findings = check_funnel_monotonicity(table, _SCHEMA)
    assert any(f.check == "funnel_monotonicity" for f in findings)


def test_funnel_monotonicity_passes_valid_funnel() -> None:
    table = [{"impressions": 1000, "clicks": 20, "conversions": 3, "reach": 800}]
    assert check_funnel_monotonicity(table, _SCHEMA) == []


def test_ctr_implausible_flagged() -> None:
    table = [{"clicks": 900, "impressions": 1000}]  # 90% CTR
    findings = check_ctr_plausibility(table, _SCHEMA)
    assert any(f.check == "ctr_implausible" for f in findings)


def test_spend_without_delivery_flagged() -> None:
    table = [{"spend": 500, "impressions": 0}]
    findings = check_spend_delivery_coherence(table, _SCHEMA)
    assert any(f.check == "spend_without_delivery" for f in findings)


def test_revenue_without_conversion_flagged() -> None:
    table = [{"revenue": 1000, "conversions": 0}]
    findings = check_revenue_conversion_coherence(table, _SCHEMA)
    assert any(f.check == "revenue_without_conversion" for f in findings)


def test_semantic_checks_run_via_engine_and_block() -> None:
    table = [
        {"date": "2026-01-01", "channel": "meta", "clicks": 50, "impressions": 5},
    ]
    flags = validate(table, _SCHEMA)
    funnel = [f for f in flags if f.check == "funnel_monotonicity"]
    assert funnel and funnel[0].severity == "blocking"


def test_no_false_positive_when_fields_absent() -> None:
    # Rows carrying only spend must never trigger funnel/CTR checks.
    table = [{"date": "2026-01-01", "channel": "meta", "spend": 100}]
    flags = validate(table, _SCHEMA)
    semantic = {"funnel_monotonicity", "ctr_implausible", "cvr_implausible"}
    assert not any(f.check in semantic for f in flags)


def test_output_statistics_min_max_mean() -> None:
    table = [
        {"spend": 10, "impressions": 100},
        {"spend": 20, "impressions": 200},
        {"spend": 30},  # null impressions
    ]
    stats = output_statistics(table, _SCHEMA)
    assert stats.row_count == 3
    spend = next(m for m in stats.measures if m.measure == "spend")
    assert spend.min == 10 and spend.max == 30 and spend.mean == 20
    impressions = next(m for m in stats.measures if m.measure == "impressions")
    assert impressions.non_null == 2
    assert impressions.null_rate == round(1 / 3, 4)
