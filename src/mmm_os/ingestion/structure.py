"""Structure detection: header-row location and column type inference (P1-3, P1-4).

Pure functions over a bounded row preview (``parsing.RawSheet.rows``). Header
detection deterministically scores candidate rows and picks the best; below a
confidence threshold the sheet is flagged for review (OQ-1.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from mmm_os.ingestion.parsing import Row
from mmm_os.models.enums import ColumnType

HEADER_SCAN_ROWS = 20
HEADER_CONFIDENCE_THRESHOLD = 0.6
TYPE_SAMPLE_LIMIT = 200

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%d %b %Y",
    "%b %d, %Y",
    "%d %B %Y",
)
_CURRENCY_CHARS = "$€£¥₹"
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
_BOOL_VALUES = {"true", "false", "yes", "no"}


@dataclass(frozen=True)
class HeaderDetection:
    """Result of header-row detection.

    Attributes:
        index: The chosen header row index, or ``None`` if none found.
        score: The confidence score of the chosen row in ``[0, 1]``.
        confident: Whether the score met the confidence threshold.
    """

    index: int | None
    score: float
    confident: bool


@dataclass(frozen=True)
class ColumnStructure:
    """Inferred structure of one column."""

    index: int
    name: str
    type: ColumnType
    date_format: str | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation."""
        return {
            "index": self.index,
            "name": self.name,
            "type": self.type.value,
            "date_format": self.date_format,
        }


def match_date(value: str) -> str | None:
    """Return the first date format matching ``value``, or ``None``."""
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(value, fmt)
        except ValueError:
            continue
        return fmt
    return None


def _strip_number(value: str) -> tuple[str, bool]:
    """Strip currency symbols/commas/parentheses; return (cleaned, had_currency)."""
    had_currency = any(ch in value for ch in _CURRENCY_CHARS)
    cleaned = value
    for ch in _CURRENCY_CHARS:
        cleaned = cleaned.replace(ch, "")
    cleaned = cleaned.replace(",", "").strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return cleaned, had_currency


def _is_number(value: str) -> tuple[bool, bool]:
    """Return (is_number, is_currency) for a raw string value."""
    cleaned, had_currency = _strip_number(value)
    return bool(_NUMBER_RE.match(cleaned)), had_currency


def parse_number(value: str) -> float | None:
    """Parse a numeric/currency string to a float, or ``None`` if not numeric."""
    cleaned, _ = _strip_number(value)
    if _NUMBER_RE.match(cleaned):
        return float(cleaned)
    return None


def _is_bool(value: str) -> bool:
    return value.strip().casefold() in _BOOL_VALUES


def _looks_like_label(cell: str) -> bool:
    """Return whether a cell reads like a header label (not a number/date)."""
    if _is_number(cell)[0] or match_date(cell) is not None:
        return False
    return len(cell) <= 128


def _score_header_row(rows: list[Row], i: int, width: int) -> float:
    """Score row ``i`` as a candidate header (higher is more header-like)."""
    row = rows[i]
    non_empty = [c for c in row if c is not None]
    if len(non_empty) < 2:
        return 0.0
    # There must be at least one data row beneath with content.
    has_data_below = any(cell is not None for below in rows[i + 1 :] for cell in below)
    if not has_data_below:
        return 0.0
    label_like = sum(1 for c in non_empty if _looks_like_label(c))
    unique = len({c.casefold() for c in non_empty})
    label_ratio = label_like / len(non_empty)
    fill_ratio = len(non_empty) / max(width, 1)
    unique_ratio = unique / len(non_empty)
    return label_ratio * 0.5 + fill_ratio * 0.3 + unique_ratio * 0.2


def detect_header(rows: list[Row]) -> HeaderDetection:
    """Detect the header row within a bounded preview.

    Args:
        rows: The sheet's previewed rows.

    Returns:
        A ``HeaderDetection`` naming the best candidate row and its confidence.
    """
    if not rows:
        return HeaderDetection(index=None, score=0.0, confident=False)
    width = max((len(r) for r in rows), default=0)
    best_index: int | None = None
    best_score = 0.0
    for i in range(min(HEADER_SCAN_ROWS, len(rows))):
        score = _score_header_row(rows, i, width)
        if score > best_score:
            best_score = score
            best_index = i
    return HeaderDetection(
        index=best_index,
        score=best_score,
        confident=best_index is not None and best_score >= HEADER_CONFIDENCE_THRESHOLD,
    )


def _infer_column_type(values: list[str]) -> tuple[ColumnType, str | None]:
    """Infer a column's type from a sample of non-null string values."""
    if not values:
        return ColumnType.STRING, None
    if all(_is_bool(v) for v in values):
        return ColumnType.BOOLEAN, None
    date_formats = [match_date(v) for v in values]
    if all(fmt is not None for fmt in date_formats):
        # Most common matching format.
        common = max(set(date_formats), key=date_formats.count)
        return ColumnType.DATE, common
    number_flags = [_is_number(v) for v in values]
    if all(is_num for is_num, _ in number_flags):
        is_currency = any(had_cur for _, had_cur in number_flags)
        return (ColumnType.CURRENCY if is_currency else ColumnType.NUMBER), None
    return ColumnType.STRING, None


def infer_columns(rows: list[Row], header_index: int | None) -> list[ColumnStructure]:
    """Infer per-column names and types from the data rows below the header.

    Args:
        rows: The sheet's previewed rows.
        header_index: The detected header row index (``None`` if unknown).

    Returns:
        One ``ColumnStructure`` per column.
    """
    if not rows:
        return []
    width = max((len(r) for r in rows), default=0)
    header_row = rows[header_index] if header_index is not None else []
    data_rows = rows[(header_index + 1) :] if header_index is not None else rows

    columns: list[ColumnStructure] = []
    for col in range(width):
        raw_name = header_row[col] if col < len(header_row) else None
        name = raw_name if raw_name else f"column_{col + 1}"
        sample: list[str] = []
        for row in data_rows:
            if col < len(row):
                cell = row[col]
                if cell is not None:
                    sample.append(cell)
            if len(sample) >= TYPE_SAMPLE_LIMIT:
                break
        col_type, date_format = _infer_column_type(sample)
        columns.append(
            ColumnStructure(index=col, name=name, type=col_type, date_format=date_format)
        )
    return columns
