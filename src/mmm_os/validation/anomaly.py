"""Statistical anomaly detection on measures (P4-2, OQ-4.2).

Flags outliers by **z-score** and **IQR** (a value is anomalous if either method
flags it), optionally within a dimension slice (``group_by``). Returns raw
``Finding`` objects; the policy assigns severity.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

from mmm_os.ingestion.structure import parse_number
from mmm_os.transform.types import Table
from mmm_os.validation.flags import Finding

_MIN_POINTS = 4


def _to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return parse_number(value) if isinstance(value, str) else float(value)


def _zscore_outliers(points: list[tuple[int, float]], threshold: float) -> set[int]:
    values = [v for _, v in points]
    mean = statistics.mean(values)
    stdev = statistics.pstdev(values)
    if stdev == 0:
        return set()
    return {i for i, v in points if abs((v - mean) / stdev) >= threshold}


def _iqr_outliers(points: list[tuple[int, float]]) -> set[int]:
    values = sorted(v for _, v in points)
    q1, _median, q3 = statistics.quantiles(values, n=4, method="inclusive")
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return {i for i, v in points if v < lower or v > upper}


def detect_anomalies(
    table: Table, measure: str, *, group_by: str | None = None, z_threshold: float = 3.0
) -> list[Finding]:
    """Detect outliers on ``measure`` (optionally per ``group_by`` slice).

    Args:
        table: The records to scan.
        measure: The measure field to analyse.
        group_by: Optional dimension to slice by before detecting outliers.
        z_threshold: The z-score threshold.

    Returns:
        Outlier findings (may be empty).
    """
    groups: dict[Any, list[tuple[int, float]]] = defaultdict(list)
    for i, row in enumerate(table):
        number = _to_number(row.get(measure))
        if number is None:
            continue
        key = row.get(group_by) if group_by else None
        groups[key].append((i, number))

    findings: list[Finding] = []
    for key, points in groups.items():
        if len(points) < _MIN_POINTS:
            continue
        values = dict(points)
        outliers = _zscore_outliers(points, z_threshold) | _iqr_outliers(points)
        for i in sorted(outliers):
            findings.append(
                Finding(
                    "anomaly",
                    f"{measure} value {values[i]} is a statistical outlier",
                    {"row": i, "field": measure, "group": key},
                )
            )
    return findings
