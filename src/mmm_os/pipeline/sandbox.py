"""In-app sandbox / test environment (Phase 18).

Runs the full pipeline (map -> transform -> validate -> output-stats) over a sheet
**without publishing** — no ``output_row`` / ``Stack`` is written, so a user can try
configs safely before committing. Reuses the same preparation as the real pipeline
so a sandbox run reflects what production would do.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from mmm_os.canonical import CanonicalConfig
from mmm_os.output.service import prepare_sheet_rows
from mmm_os.storage.base import ObjectStorage
from mmm_os.transform.types import Table
from mmm_os.validation.engine import validate
from mmm_os.validation.stats import OutputStats, output_statistics


@dataclass
class SandboxResult:
    """The throwaway result of a sandbox run (nothing persisted as real output)."""

    sheet_id: uuid.UUID
    row_count: int
    sample_rows: Table = field(default_factory=list)
    flag_counts: dict[str, int] = field(default_factory=dict)
    blocking: bool = False
    stats: OutputStats | None = None


def run_sandbox(
    session: Session,
    storage: ObjectStorage,
    canonical: CanonicalConfig,
    *,
    tenant_id: uuid.UUID,
    sheet_id: uuid.UUID,
    sample: int = 20,
    row_limit: int = 1000,
) -> SandboxResult:
    """Dry-run a sheet through the pipeline; return results without persisting output.

    Validation runs in memory (flags are **not** written to the DB), and no
    ``output_row`` / ``Stack`` is created — the run is purely a preview.
    """
    prepared = prepare_sheet_rows(
        session, storage, canonical, tenant_id=tenant_id, sheet_id=sheet_id, limit=row_limit
    )
    flags = validate(prepared.rows, canonical.schema)
    counts = Counter(f.severity for f in flags)
    return SandboxResult(
        sheet_id=sheet_id,
        row_count=len(prepared.rows),
        sample_rows=prepared.rows[:sample],
        flag_counts=dict(counts),
        blocking=any(f.severity == "blocking" for f in flags),
        stats=output_statistics(prepared.rows, canonical.schema),
    )
