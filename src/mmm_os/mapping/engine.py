"""Mapping application and required-field validation (P2-1, P2-5).

Pure functions: given a sheet's detected columns and a mapping
``{source_name: canonical_field | None}``, partition the columns into mapped /
ignored / invalid and report any missing required canonical fields (OQ-2.2). No
persistence — saved configs live in 02.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mmm_os.canonical.models import CanonicalSchema


@dataclass(frozen=True)
class MappedColumn:
    """A source column mapped to a canonical field."""

    source_name: str
    canonical_field: str


@dataclass(frozen=True)
class MappingResult:
    """The outcome of applying a mapping to a sheet's columns.

    Attributes:
        mapped: Columns mapped to a valid canonical field.
        ignored: Source columns with no (or null) mapping.
        invalid: Source columns mapped to a name that is not a canonical field.
        missing_required: Required canonical fields not satisfied by the mapping.
    """

    mapped: list[MappedColumn]
    ignored: list[str]
    invalid: list[str]
    missing_required: list[str]

    @property
    def is_complete(self) -> bool:
        """Whether all required fields are mapped (output is not blocked)."""
        return not self.missing_required


def _mappable_fields(schema: CanonicalSchema) -> set[str]:
    """Return the canonical fields a source column may map to.

    Dimensions + measures + factors (MMM external regressors); a factor source
    maps its columns to factor fields (Cycle 2).
    """
    return {f.name for f in (*schema.dimensions, *schema.measures, *schema.factors)}


def _missing_required(targets: set[str], schema: CanonicalSchema) -> list[str]:
    """Return required canonical fields not present in ``targets`` (OQ-2.2).

    A row is meaningful with at least ``min_required`` measures OR at least one
    factor (factor sources carry no media measures).
    """
    missing = [f.name for f in schema.dimensions if f.required and f.name not in targets]
    measure_names = {f.name for f in schema.measures}
    has_factor = bool(targets & schema.factor_names())
    if len(targets & measure_names) < schema.measure_policy.min_required and not has_factor:
        missing.append(f"at_least_{schema.measure_policy.min_required}_measure_or_factor")
    return missing


def apply_mapping(
    columns: list[dict[str, Any]], mapping: dict[str, str | None], schema: CanonicalSchema
) -> MappingResult:
    """Apply a column mapping and validate required fields.

    Args:
        columns: Detected column structures (dicts with a ``name`` key).
        mapping: ``{source_name: canonical_field | None}`` (null/absent = ignored).
        schema: The canonical schema (valid targets + required policy).

    Returns:
        A ``MappingResult`` partitioning the columns and listing missing required fields.
    """
    valid = _mappable_fields(schema)
    mapped: list[MappedColumn] = []
    ignored: list[str] = []
    invalid: list[str] = []

    for col in columns:
        source = str(col["name"])
        target = mapping.get(source)
        if not target:
            ignored.append(source)
        elif target in valid:
            mapped.append(MappedColumn(source_name=source, canonical_field=target))
        else:
            invalid.append(source)

    targets = {m.canonical_field for m in mapped}
    return MappingResult(
        mapped=mapped,
        ignored=ignored,
        invalid=invalid,
        missing_required=_missing_required(targets, schema),
    )


def map_rows(
    rows: list[dict[str, Any]], mapping: dict[str, str | None]
) -> list[dict[str, Any]]:
    """Rename each row's keys from source column name to canonical field.

    Columns with no (or null) mapping are dropped, matching ``apply_mapping``'s
    treatment of "ignored" columns.

    Args:
        rows: Records keyed by source column name.
        mapping: ``{source_name: canonical_field | None}`` (null/absent = dropped).

    Returns:
        Records keyed by canonical field name.
    """
    return [
        {target: row[source] for source, target in mapping.items() if target and source in row}
        for row in rows
    ]
