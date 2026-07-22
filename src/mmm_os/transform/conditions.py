"""Row-level condition evaluation for transformation rules.

A condition is a small dict predicate, e.g. ``{"field": "channel", "op": "eq",
"value": "Facebook"}``. Supported ops: ``eq``, ``ne``, ``in``, ``not_in``,
``is_null``, ``not_null``. A ``None`` condition matches every row.
"""

from __future__ import annotations

from typing import Any

from mmm_os.transform.types import Row


def matches(row: Row, condition: dict[str, Any] | None) -> bool:
    """Return whether ``row`` satisfies ``condition``.

    Args:
        row: The record to test.
        condition: The predicate, or ``None`` (always matches).

    Returns:
        ``True`` if the row matches (or no condition given).
    """
    if not condition:
        return True
    field = condition.get("field")
    op = condition.get("op", "eq")
    value = condition.get("value")
    actual = row.get(field) if field is not None else None

    if op == "eq":
        return actual == value
    if op == "ne":
        return actual != value
    if op == "in":
        return actual in value if isinstance(value, (list, tuple, set)) else False
    if op == "not_in":
        return actual not in value if isinstance(value, (list, tuple, set)) else True
    if op == "is_null":
        return actual is None
    if op == "not_null":
        return actual is not None
    return False
