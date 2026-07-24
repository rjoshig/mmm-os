"""Stage 2 — harmonization & Stack assembly (Gold layer, Phase 16)."""

from mmm_os.stack.harmonize import HarmonizationSpec, harmonize_rows, suggest_harmonization
from mmm_os.stack.service import (
    assemble_stack,
    get_stack,
    list_stacks,
    publish_stack,
    stack_rows_as_dicts,
    validate_panel,
)

__all__ = [
    "HarmonizationSpec",
    "assemble_stack",
    "get_stack",
    "harmonize_rows",
    "list_stacks",
    "publish_stack",
    "stack_rows_as_dicts",
    "suggest_harmonization",
    "validate_panel",
]
