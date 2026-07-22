"""Core types for the transformation rule engine.

The engine operates on in-memory **records**: a ``Table`` is a list of ``Row``
dicts keyed by field name (canonical fields after mapping). A ``RuleSpec`` is the
declarative rule shape (Appendix D) the engine applies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Row = dict[str, Any]
Table = list[Row]

# Layer application order: global first so customer overrides win last.
_LAYER_RANK = {"global": 0, "template": 1, "customer": 2}


@dataclass(frozen=True)
class RuleSpec:
    """A single declarative transformation rule.

    Attributes:
        target_field: The canonical field (or source column) the rule acts on.
        operation: The registered operation name.
        params: Operation-specific parameters.
        condition: Optional per-row predicate; ``None`` applies to all rows.
        order: Deterministic application order within a layer.
        layer: One of ``global`` / ``template`` / ``customer``.
    """

    target_field: str
    operation: str
    params: dict[str, Any] = field(default_factory=dict)
    condition: dict[str, Any] | None = None
    order: int = 0
    layer: str = "customer"

    def sort_key(self) -> tuple[int, int]:
        """Return the (layer rank, order) key used to sort rules deterministically."""
        return (_LAYER_RANK.get(self.layer, 99), self.order)
