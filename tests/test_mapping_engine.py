"""Unit tests for the mapping engine and column signature (02.1)."""

from __future__ import annotations

from mmm_os.canonical import load_canonical_schema
from mmm_os.mapping.engine import apply_mapping
from mmm_os.mapping.signature import column_signature, normalize_name


def _cols(*names: str) -> list[dict[str, str]]:
    return [{"name": n} for n in names]


def test_normalize_name() -> None:
    """Names are lowercased with punctuation/whitespace collapsed to underscores."""
    assert normalize_name("Spend ($)") == "spend"
    assert normalize_name("  Ad Group ") == "ad_group"
    assert normalize_name("CHANNEL") == "channel"


def test_signature_is_order_tolerant() -> None:
    """The same set of names in different orders yields the same signature."""
    a = column_signature(_cols("date", "channel", "spend"))
    b = column_signature(_cols("spend", "date", "channel"))
    assert a == b


def test_signature_differs_on_different_columns() -> None:
    """A different column set produces a different signature."""
    a = column_signature(_cols("date", "channel", "spend"))
    b = column_signature(_cols("date", "channel", "impressions"))
    assert a != b


def test_apply_mapping_partitions_columns() -> None:
    """Columns partition into mapped / ignored / invalid."""
    schema = load_canonical_schema()
    columns = _cols("Date", "Chan", "Spend", "Notes")
    mapping = {
        "Date": "date",
        "Chan": "channel",
        "Spend": "spend",
        "Notes": None,  # ignored
    }
    result = apply_mapping(columns, mapping, schema)
    assert {m.source_name for m in result.mapped} == {"Date", "Chan", "Spend"}
    assert result.ignored == ["Notes"]
    assert result.invalid == []
    assert result.is_complete


def test_apply_mapping_flags_invalid_target() -> None:
    """A target that is not a canonical field is reported invalid."""
    schema = load_canonical_schema()
    result = apply_mapping(_cols("X"), {"X": "not_a_field"}, schema)
    assert result.invalid == ["X"]
    assert not result.is_complete


def test_missing_required_blocks_completion() -> None:
    """Missing channel or missing all measures makes the mapping incomplete."""
    schema = load_canonical_schema()

    no_channel = apply_mapping(_cols("Date", "Spend"), {"Date": "date", "Spend": "spend"}, schema)
    assert "channel" in no_channel.missing_required
    assert not no_channel.is_complete

    no_measure = apply_mapping(_cols("Date", "Chan"), {"Date": "date", "Chan": "channel"}, schema)
    assert any("measure" in m for m in no_measure.missing_required)
    assert not no_measure.is_complete


def test_factor_source_completes_without_a_measure() -> None:
    """A factor source (date + channel + a factor, no measure) maps completely (Cycle 2)."""
    schema = load_canonical_schema()
    result = apply_mapping(
        _cols("Week", "Chan", "Price"),
        {"Week": "date", "Chan": "channel", "Price": "price_index"},
        schema,
    )
    assert result.is_complete
    assert not result.missing_required
    assert "price_index" in {m.canonical_field for m in result.mapped}
