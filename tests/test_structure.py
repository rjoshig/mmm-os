"""Unit tests for header detection and column type inference (01.2)."""

from __future__ import annotations

from mmm_os.ingestion.structure import detect_header, infer_columns, match_date
from mmm_os.models.enums import ColumnType


def test_detect_header_skips_title_rows() -> None:
    """The header is found beneath title/blank rows, not on row 0."""
    rows = [
        ["Monthly Marketing Export", None, None],
        [None, None, None],
        ["date", "channel", "spend"],
        ["2026-01-01", "Facebook", "100"],
        ["2026-01-02", "Google", "200"],
    ]
    detection = detect_header(rows)
    assert detection.index == 2
    assert detection.confident


def test_detect_header_on_clean_sheet() -> None:
    """A clean sheet has its header on row 0."""
    rows = [
        ["date", "channel", "spend"],
        ["2026-01-01", "Facebook", "100"],
    ]
    detection = detect_header(rows)
    assert detection.index == 0
    assert detection.confident


def test_infer_columns_types() -> None:
    """Column types are inferred from data below the header."""
    rows = [
        ["date", "channel", "spend", "active"],
        ["2026-01-01", "Facebook", "$1,200.50", "true"],
        ["2026-01-02", "Google", "800", "false"],
    ]
    columns = infer_columns(rows, header_index=0)
    by_name = {c.name: c for c in columns}
    assert by_name["date"].type is ColumnType.DATE
    assert by_name["date"].date_format == "%Y-%m-%d"
    assert by_name["channel"].type is ColumnType.STRING
    assert by_name["spend"].type is ColumnType.CURRENCY
    assert by_name["active"].type is ColumnType.BOOLEAN


def test_infer_columns_without_header_names_are_synthesised() -> None:
    """When no header is detected, columns get synthetic names."""
    columns = infer_columns([["1", "2"], ["3", "4"]], header_index=None)
    assert [c.name for c in columns] == ["column_1", "column_2"]
    assert all(c.type is ColumnType.NUMBER for c in columns)


def test_match_date_formats() -> None:
    """A few common date formats are recognised."""
    assert match_date("2026-01-01") == "%Y-%m-%d"
    assert match_date("01/02/2026") == "%d/%m/%Y"
    assert match_date("not a date") is None
