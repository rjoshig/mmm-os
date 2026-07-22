"""Column signature for reusing mapping configs (OQ-2.1).

A signature is the **normalized set of a sheet's header names** — lowercased,
trimmed, with whitespace/punctuation collapsed — joined in sorted order. It is
order-tolerant: the same set of column names always yields the same signature.
Fuzzy/positional matching is deferred to the AI layer (Phase 5).
"""

from __future__ import annotations

import re
from typing import Any

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Normalise a column name to lowercase underscore-joined tokens.

    Args:
        name: The raw column name.

    Returns:
        The normalised name (e.g. ``"Spend ($)"`` → ``"spend"``).
    """
    lowered = name.strip().lower()
    return _NON_ALNUM.sub(" ", lowered).strip().replace(" ", "_")


def column_signature(columns: list[dict[str, Any]]) -> str:
    """Compute an order-tolerant signature from detected columns.

    Args:
        columns: Detected column structures (dicts with a ``name`` key).

    Returns:
        A stable signature string (sorted, ``|``-joined normalised names).
    """
    names = {normalize_name(str(col["name"])) for col in columns if col.get("name")}
    names.discard("")
    return "|".join(sorted(names))
