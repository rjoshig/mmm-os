"""Severity policy and blocking gate (P4-4, OQ-4.1).

Maps each check to a severity. Default: BLOCK for missing required fields,
negative measures, and required-field type mismatches; WARN for date gaps,
duplicates, non-required type mismatches, out-of-range, and anomalies. The policy
is configurable per tenant via overrides.
"""

from __future__ import annotations

from collections.abc import Iterable

from mmm_os.models.enums import Severity
from mmm_os.validation.flags import Flag

DEFAULT_POLICY: dict[str, str] = {
    "missing_required": Severity.BLOCKING.value,
    "negative_measure": Severity.BLOCKING.value,
    "type_mismatch_required": Severity.BLOCKING.value,
    "type_mismatch": Severity.WARNING.value,
    "duplicate_row": Severity.WARNING.value,
    "date_gap": Severity.WARNING.value,
    "zero_spend": Severity.INFO.value,
    "out_of_range": Severity.WARNING.value,
    "anomaly": Severity.WARNING.value,
}


class Policy:
    """A configurable check → severity policy."""

    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        """Initialise the policy.

        Args:
            overrides: Optional per-check severity overrides.
        """
        self._map = {**DEFAULT_POLICY, **(overrides or {})}

    def severity_for(self, check: str) -> str:
        """Return the severity for a check (defaults to warning)."""
        return self._map.get(check, Severity.WARNING.value)


def is_blocked(flags: Iterable[Flag]) -> bool:
    """Return whether any flag has blocking severity (output is gated)."""
    return any(flag.severity == Severity.BLOCKING.value for flag in flags)
