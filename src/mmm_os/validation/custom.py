"""Tenant-authored custom validation checks (Phase 21, CC-4/ADR-004).

Each custom check is a sandboxed boolean expression (e.g. ``clicks <= impressions``)
evaluated per row against the row's fields. A row where the expression is False (or
errors) yields a ``Finding``. Reuses the transform sandbox evaluator — no arbitrary
code (ADR-004).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from mmm_os.ingestion.structure import parse_number
from mmm_os.models.enums import Severity
from mmm_os.transform.operations_custom import SandboxError, evaluate
from mmm_os.transform.types import Table
from mmm_os.validation.flags import Finding, Flag


def _numeric_namespace(row: dict[str, object]) -> dict[str, object]:
    """Coerce numeric-looking string cells to floats so comparisons are numeric.

    Marketing measures often arrive as strings (e.g. ``"100"``); without this a rule
    like ``clicks <= impressions`` would compare strings lexicographically. Non-numeric
    strings (channel names, dates) are left untouched.
    """
    out: dict[str, object] = {}
    for key, value in row.items():
        if isinstance(value, str):
            number = parse_number(value)
            out[key] = number if number is not None else value
        else:
            out[key] = value
    return out


@dataclass(frozen=True)
class ValidationRuleSpec:
    """A tenant-authored validation rule to run per row (Part 3).

    Attributes:
        name: The rule's display name (appears in the flag's check + description).
        expression: A sandboxed boolean expression that must be truthy to pass.
        severity: The severity assigned to a flag when the expression fails
            (``info`` / ``warning`` / ``blocking``); applied directly, not via the
            global policy, so each rule blocks or warns independently.
    """

    name: str
    expression: str
    severity: str = Severity.WARNING.value


def run_validation_rules(table: Table, rules: Sequence[ValidationRuleSpec]) -> list[Flag]:
    """Run tenant validation rules over ``table``; return severity-assigned flags.

    Each rule's expression is evaluated per row in the AST sandbox (ADR-004). A row
    where the expression is falsy — or the expression is unsafe/malformed — yields a
    ``Flag`` carrying the rule's own severity (check name ``custom:<name>``).
    """
    flags: list[Flag] = []
    for rule in rules:
        for i, row in enumerate(table):
            check = f"custom:{rule.name}"
            try:
                ok = bool(evaluate(rule.expression, _numeric_namespace(dict(row))))
            except SandboxError:
                flags.append(
                    Flag(
                        check,
                        rule.severity,
                        f"custom rule {rule.name!r} could not be evaluated",
                        {"row": i, "check_name": rule.name},
                    )
                )
                continue
            if not ok:
                flags.append(
                    Flag(
                        check,
                        rule.severity,
                        f"custom rule {rule.name!r} failed",
                        {"row": i, "check_name": rule.name},
                    )
                )
    return flags


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
