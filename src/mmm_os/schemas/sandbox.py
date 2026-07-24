"""Schemas for the in-app sandbox / test environment (Phase 18)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel

from mmm_os.schemas.output import MeasureStatsRead


class SandboxRunResponse(BaseModel):
    """The throwaway result of a sandbox run (nothing persisted as real output)."""

    sheet_id: uuid.UUID
    is_sandbox: bool = True
    row_count: int
    sample_rows: list[dict[str, Any]]
    flag_counts: dict[str, int]
    blocking: bool
    row_count_stats: int
    measures: list[MeasureStatsRead]
