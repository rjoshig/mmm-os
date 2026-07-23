"""Canonical output generation (the final pipeline step).

Takes a sheet's mapped + transformed + validated rows and persists them as clean,
canonically-keyed ``OutputRow`` records with full traceability (CC-3). This is
the "out" half of the platform's stated file-in → clean-data-out MVP — previously
defined but never populated.
"""

from mmm_os.output.service import (
    generate_output,
    has_open_blocking_flags,
    list_output_rows,
    prepare_sheet_rows,
)

__all__ = [
    "generate_output",
    "has_open_blocking_flags",
    "list_output_rows",
    "prepare_sheet_rows",
]
