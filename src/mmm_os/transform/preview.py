"""Before/after preview of a rule set on sample rows (P3-7).

Applies rules to a bounded sample and returns both the original and transformed
records **without persisting anything** — this powers the UI later.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from mmm_os.transform.engine import apply_rules
from mmm_os.transform.registry import RuleContext
from mmm_os.transform.types import RuleSpec, Table


@dataclass(frozen=True)
class PreviewResult:
    """The before/after of a preview."""

    before: Table
    after: Table


def preview(
    rows: Table, rules: list[RuleSpec], ctx: RuleContext | None = None, *, limit: int | None = None
) -> PreviewResult:
    """Return before/after for a rule set on sample rows, persisting nothing.

    Args:
        rows: The sample records.
        rules: The rules to apply.
        ctx: Optional context (taxonomies, …).
        limit: Optional cap on the number of sample rows previewed.

    Returns:
        A ``PreviewResult`` with the original and transformed records.
    """
    sample = rows[:limit] if limit is not None else rows
    before = copy.deepcopy(sample)
    after = apply_rules(sample, rules, ctx)
    return PreviewResult(before=before, after=after)
