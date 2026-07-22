"""Unit tests for the rule engine core and structural operations (03.1)."""

from __future__ import annotations

import pytest

from mmm_os.transform.engine import apply_rules
from mmm_os.transform.registry import UnknownOperationError, registered_operations
from mmm_os.transform.types import RuleSpec


def test_unknown_operation_raises() -> None:
    """An unregistered operation raises a clear error."""
    with pytest.raises(UnknownOperationError):
        apply_rules([{"a": 1}], [RuleSpec(target_field="a", operation="nope")])


def test_core_operations_registered() -> None:
    """The structural operations are registered."""
    ops = set(registered_operations())
    assert {"rename_column", "cast_type", "normalize_text", "fill_missing", "dedupe"} <= ops


def test_apply_is_pure_and_deterministic() -> None:
    """The input is not mutated and repeated runs are identical (idempotent)."""
    table = [{"spend": "100"}]
    rules = [RuleSpec(target_field="spend", operation="cast_type", params={"to": "number"})]
    out1 = apply_rules(table, rules)
    out2 = apply_rules(table, rules)
    assert out1 == out2 == [{"spend": 100.0}]
    assert table == [{"spend": "100"}]  # original untouched


def test_layer_and_order_precedence() -> None:
    """Rules apply by (layer, order): global then customer, each by order."""
    table = [{"v": "x"}]
    rules = [
        RuleSpec(
            target_field="v",
            operation="fill_missing",
            params={"value": "z"},
            layer="customer",
            order=1,
        ),
        RuleSpec(
            target_field="v",
            operation="normalize_text",
            params={"upper": True},
            layer="global",
            order=0,
        ),
    ]
    # global normalize (x->X) runs first, then customer fill (no-op since not null).
    assert apply_rules(table, rules) == [{"v": "X"}]


def test_rename_cast_fill_normalize() -> None:
    """Each structural op transforms records as expected."""
    table = [{"Spend": " 100 ", "chan": None}]
    rules = [
        RuleSpec(target_field="Spend", operation="rename_column", params={"to": "spend"}, order=0),
        RuleSpec(target_field="spend", operation="normalize_text", params={"strip": True}, order=1),
        RuleSpec(target_field="spend", operation="cast_type", params={"to": "number"}, order=2),
        RuleSpec(target_field="chan", operation="fill_missing", params={"value": "Other"}, order=3),
    ]
    assert apply_rules(table, rules) == [{"spend": 100.0, "chan": "Other"}]


def test_dedupe_by_keys() -> None:
    """dedupe keeps the first row per key set."""
    table = [
        {"date": "2026-01-01", "channel": "FB", "spend": "1"},
        {"date": "2026-01-01", "channel": "FB", "spend": "2"},
        {"date": "2026-01-02", "channel": "FB", "spend": "3"},
    ]
    rules = [RuleSpec(target_field="", operation="dedupe", params={"keys": ["date", "channel"]})]
    out = apply_rules(table, rules)
    assert len(out) == 2
    assert out[0]["spend"] == "1"


def test_condition_restricts_rows() -> None:
    """A condition applies an op only to matching rows."""
    table = [{"channel": "FB", "note": "x"}, {"channel": "Google", "note": "x"}]
    rules = [
        RuleSpec(
            target_field="note",
            operation="normalize_text",
            params={"upper": True},
            condition={"field": "channel", "op": "eq", "value": "FB"},
        )
    ]
    out = apply_rules(table, rules)
    assert out[0]["note"] == "X"
    assert out[1]["note"] == "x"
