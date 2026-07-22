"""Unit tests for value operations and the sandbox (03.2)."""

from __future__ import annotations

import pytest

from mmm_os.canonical import load_taxonomies
from mmm_os.transform.engine import apply_rules
from mmm_os.transform.operations_custom import SandboxError, evaluate
from mmm_os.transform.registry import RuleContext
from mmm_os.transform.types import RuleSpec


def test_map_value_collapses_taxonomy_spellings() -> None:
    """map_value collapses raw channel spellings to the canonical term (P3-6)."""
    ctx = RuleContext(taxonomies=load_taxonomies())
    table = [{"channel": "FB"}, {"channel": "fb_ads"}, {"channel": "facebook ads"}]
    rules = [
        RuleSpec(target_field="channel", operation="map_value", params={"taxonomy": "channel"})
    ]
    out = apply_rules(table, rules, ctx)
    assert {r["channel"] for r in out} == {"Facebook"}


def test_parse_date_and_convert_currency_and_dedupe_in_order() -> None:
    """parse_date + convert_currency + dedupe apply in order deterministically."""
    table = [
        {"date": "01/02/2026", "spend": "100", "currency": "EUR"},
        {"date": "01/02/2026", "spend": "100", "currency": "EUR"},  # duplicate
    ]
    rules = [
        RuleSpec(
            target_field="date", operation="parse_date", params={"formats": ["%d/%m/%Y"]}, order=0
        ),
        RuleSpec(
            target_field="spend",
            operation="convert_currency",
            params={"rates": {"EUR": 1.1}, "currency_field": "currency"},
            order=1,
        ),
        RuleSpec(target_field="", operation="dedupe", params={"keys": ["date", "spend"]}, order=2),
    ]
    out = apply_rules(table, rules)
    assert len(out) == 1
    assert out[0]["date"] == "2026-02-01"
    assert out[0]["spend"] == pytest.approx(110.0)


def test_reshape_wide_to_long() -> None:
    """reshape unpivots value columns into var/value rows (OQ-3.2)."""
    table = [{"date": "2026-01-01", "facebook": "100", "google": "200"}]
    rules = [
        RuleSpec(
            target_field="",
            operation="reshape",
            params={
                "id_vars": ["date"],
                "value_vars": ["facebook", "google"],
                "var_name": "channel",
                "value_name": "spend",
            },
        )
    ]
    out = apply_rules(table, rules)
    assert out == [
        {"date": "2026-01-01", "channel": "facebook", "spend": "100"},
        {"date": "2026-01-01", "channel": "google", "spend": "200"},
    ]


def test_sandbox_allows_safe_expressions() -> None:
    """The sandbox evaluates arithmetic, comparisons, and allowlisted calls."""
    assert evaluate("spend * 2 + 1", {"spend": 10}) == 21
    assert evaluate("upper(channel)", {"channel": "fb"}) == "FB"
    assert evaluate("spend if spend > 0 else 0", {"spend": -5}) == 0
    assert evaluate("coalesce(a, b, 'x')", {"a": None, "b": None}) == "x"


def test_sandbox_blocks_unsafe_expressions() -> None:
    """Attribute access, imports, and unknown names/calls are rejected."""
    for expr in ("__import__('os')", "spend.__class__", "open('x')", "().__class__"):
        with pytest.raises(SandboxError):
            evaluate(expr, {"spend": 1})


def test_custom_op_assigns_expression_result() -> None:
    """The custom op writes the evaluated expression to the output field."""
    table = [{"clicks": 50, "impressions": 1000}]
    rules = [
        RuleSpec(
            target_field="ctr",
            operation="custom",
            params={"expression": "round(clicks / impressions, 3)", "output": "ctr"},
        )
    ]
    out = apply_rules(table, rules)
    assert out[0]["ctr"] == 0.05
