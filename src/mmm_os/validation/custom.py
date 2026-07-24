"""Tenant-authored custom validation checks (Phase 21, CC-4/ADR-004).

Each custom check is a sandboxed boolean expression (e.g. ``clicks <= impressions``)
evaluated per row against the row's fields. A row where the expression is False (or
errors) yields a ``Finding``. Reuses the transform sandbox evaluator — no arbitrary
code (ADR-004).
"""

from __future__ import annotations

from collections.abc import Sequence

from mmm_os.transform.operations_custom import SandboxError, evaluate
from mmm_os.transform.types import Table
from mmm_os.validation.flags import Finding


def run_custom_checks(table: Table, checks: Sequence[tuple[str, str]]) -> list[Finding]:
    """Run tenant custom checks over ``table``; return findings for failing rows.

    Args:
        table: The canonical-keyed rows to validate.
        checks: ``(name, expression)`` pairs; each expression must evaluate truthy
            for a row to pass.

    Returns:
        Findings (check name ``custom_check``) for rows that fail or error.
    """
    findings: list[Finding] = []
    for name, expression in checks:
        for i, row in enumerate(table):
            try:
                ok = bool(evaluate(expression, dict(row)))
            except SandboxError:
                # A malformed/unsafe expression flags the row rather than crashing.
                findings.append(
                    Finding(
                        "custom_check",
                        f"custom check {name!r} could not be evaluated",
                        {"row": i, "check_name": name},
                    )
                )
                continue
            if not ok:
                findings.append(
                    Finding(
                        "custom_check",
                        f"custom check {name!r} failed",
                        {"row": i, "check_name": name},
                    )
                )
    return findings
