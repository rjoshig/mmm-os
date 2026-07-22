"""Per-column profiling (P1-5).

Streams a sheet's data rows and accumulates bounded per-column stats — distinct
count, sample values, null rate, and min/max — storing **distinct values + stats
only** (never full row dumps) so the profile can safely feed the AI layer (Phase 5).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from mmm_os.ingestion.parsing import Row
from mmm_os.ingestion.structure import parse_number
from mmm_os.models.enums import ColumnType

_NUMERIC_TYPES = {ColumnType.NUMBER.value, ColumnType.CURRENCY.value}


@dataclass
class _ColumnAccumulator:
    """Mutable per-column profiling state."""

    index: int
    name: str
    type: str
    non_null: int = 0
    distinct: set[str] = field(default_factory=set)
    distinct_capped: bool = False
    samples: list[str] = field(default_factory=list)
    num_min: float | None = None
    num_max: float | None = None
    str_min: str | None = None
    str_max: str | None = None

    def observe(self, cell: str, *, distinct_limit: int, sample_limit: int) -> None:
        """Fold a single non-null cell value into the accumulator."""
        self.non_null += 1
        if len(self.distinct) < distinct_limit:
            self.distinct.add(cell)
        elif cell not in self.distinct:
            self.distinct_capped = True
        if cell not in self.samples and len(self.samples) < sample_limit:
            self.samples.append(cell)
        if self.type in _NUMERIC_TYPES:
            value = parse_number(cell)
            if value is not None:
                self.num_min = value if self.num_min is None else min(self.num_min, value)
                self.num_max = value if self.num_max is None else max(self.num_max, value)
        else:
            self.str_min = cell if self.str_min is None else min(self.str_min, cell)
            self.str_max = cell if self.str_max is None else max(self.str_max, cell)

    def to_stats(self, row_count: int) -> dict[str, Any]:
        """Render the accumulated state as a JSON-serialisable stats dict."""
        null_count = row_count - self.non_null
        is_numeric = self.type in _NUMERIC_TYPES
        return {
            "index": self.index,
            "name": self.name,
            "type": self.type,
            "distinct_count": len(self.distinct),
            "distinct_capped": self.distinct_capped,
            "sample_values": self.samples,
            "null_count": null_count,
            "null_rate": (null_count / row_count) if row_count else 0.0,
            "min": self.num_min if is_numeric else self.str_min,
            "max": self.num_max if is_numeric else self.str_max,
        }


def profile_rows(
    rows: Iterable[Row],
    columns: list[dict[str, Any]],
    header_index: int | None,
    *,
    distinct_limit: int,
    sample_limit: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Compute per-column stats over a sheet's rows.

    Args:
        rows: The full row iterator for the sheet (including header/title rows).
        columns: The detected column structures (dicts with index/name/type).
        header_index: The header row index (rows up to and including it are skipped).
        distinct_limit: Cap on distinct values tracked per column.
        sample_limit: Cap on sample values kept per column.

    Returns:
        A tuple of ``(data_row_count, per_column_stats)``.
    """
    accumulators = [
        _ColumnAccumulator(index=col["index"], name=col["name"], type=col["type"])
        for col in columns
    ]
    skip = (header_index + 1) if header_index is not None else 0

    row_count = 0
    for row_index, row in enumerate(rows):
        if row_index < skip:
            continue
        if all(cell is None for cell in row):
            continue
        row_count += 1
        for acc in accumulators:
            cell = row[acc.index] if acc.index < len(row) else None
            if cell is not None:
                acc.observe(cell, distinct_limit=distinct_limit, sample_limit=sample_limit)

    return row_count, [acc.to_stats(row_count) for acc in accumulators]
