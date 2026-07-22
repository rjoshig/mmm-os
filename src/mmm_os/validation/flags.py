"""Value types for validation findings and flags."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    """A raw check result before a severity is assigned.

    Attributes:
        check: The check name (e.g. ``duplicate_row``).
        description: A human-readable description of the issue.
        location: Where the issue is (row index, field, group, …).
    """

    check: str
    description: str
    location: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Flag:
    """A validation finding with an assigned severity."""

    check: str
    severity: str
    description: str
    location: dict[str, Any] = field(default_factory=dict)
