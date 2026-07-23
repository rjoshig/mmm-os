"""The transformation engine: ordered, layered, deterministic rule application.

Rules are sorted by (layer rank, order) and applied in sequence via their
registered handlers. The engine copies its input so application is pure
(idempotent, CC-6): the same table + rules always yield the same output.
"""

from __future__ import annotations

import copy

# Import the operation modules for their registration side effects.
from mmm_os.transform import (
    operations_aggregate,  # noqa: F401  (registers handlers)
    operations_core,  # noqa: F401
    operations_custom,  # noqa: F401
    operations_value,  # noqa: F401
)
from mmm_os.transform.registry import RuleContext, get_handler
from mmm_os.transform.types import RuleSpec, Table


def apply_rules(table: Table, rules: list[RuleSpec], ctx: RuleContext | None = None) -> Table:
    """Apply an ordered, layered set of rules to a table.

    Args:
        table: The input records (not mutated).
        rules: The rules to apply (sorted internally by layer + order).
        ctx: Optional ambient context (taxonomies, …).

    Returns:
        A new table with all rules applied in deterministic order.
    """
    context = ctx or RuleContext()
    result: Table = copy.deepcopy(table)
    for rule in sorted(rules, key=RuleSpec.sort_key):
        handler = get_handler(rule.operation)
        result = handler(result, rule, context)
    return result
