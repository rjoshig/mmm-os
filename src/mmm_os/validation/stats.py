"""Output statistics for model-ready data (Phase 17, P17-3).

Per-measure min / max / mean / median / stddev / null-rate / counts computed on a
generated output (or an assembled Stack panel), surfaced before publish so a
reviewer can sanity-check magnitudes. Pure over canonical-keyed rows.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from mmm_os.canonical.models import CanonicalSchema
from mmm_os.ingestion.structure import parse_number
from mmm_os.transform.types import Table


@dataclass(frozen=True)
class MeasureStats:
    """Summary statistics for one measure across a table."""

    measure: str
    count: int  # total rows considered
    non_null: int
    null_rate: float
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    stddev: float | None = None


@dataclass(frozen=True)
class OutputStats:
    """Row count plus per-measure statistics for an output/panel."""

    row_count: int
    measures: list[MeasureStats] = field(default_factory=list)


def _num(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return parse_number(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def measure_stats(table: Table, measure: str) -> MeasureStats:
    """Compute summary statistics for a single measure over ``table``."""
    total = len(table)
    values = [n for row in table if (n := _num(row.get(measure))) is not None]
    non_null = len(values)
    null_rate = round(1 - non_null / total, 4) if total else 0.0
    if not values:
        return MeasureStats(measure=measure, count=total, non_null=0, null_rate=null_rate)
    return MeasureStats(
        measure=measure,
        count=total,
        non_null=non_null,
        null_rate=null_rate,
        min=min(values),
        max=max(values),
        mean=round(statistics.fmean(values), 6),
        median=round(statistics.median(values), 6),
        stddev=round(statistics.pstdev(values), 6) if non_null > 1 else 0.0,
    )


def output_statistics(table: Table, schema: CanonicalSchema) -> OutputStats:
    """Compute per-measure statistics for every canonical measure present in ``table``."""
    present: set[str] = set()
    for row in table:
        present |= set(row)
    measures = [f.name for f in schema.measures if f.name in present]
    return OutputStats(
        row_count=len(table),
        measures=[measure_stats(table, m) for m in measures],
    )
