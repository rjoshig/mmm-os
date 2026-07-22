"""Validation engine: run checks and assign severities via the policy."""

from __future__ import annotations

from collections.abc import Iterable

from mmm_os.canonical.models import CanonicalSchema
from mmm_os.transform.types import Table
from mmm_os.validation.checks import ALL_CHECKS
from mmm_os.validation.flags import Finding, Flag
from mmm_os.validation.policy import Policy


def finalize(findings: Iterable[Finding], policy: Policy) -> list[Flag]:
    """Attach a severity to each finding using the policy.

    Args:
        findings: Raw findings from checks/anomaly detection.
        policy: The severity policy.

    Returns:
        The findings as severity-assigned flags.
    """
    return [
        Flag(
            check=finding.check,
            severity=policy.severity_for(finding.check),
            description=finding.description,
            location=finding.location,
        )
        for finding in findings
    ]


def validate(table: Table, schema: CanonicalSchema, policy: Policy | None = None) -> list[Flag]:
    """Run all validation checks over a table and return severity-assigned flags.

    Args:
        table: The records to validate.
        schema: The canonical schema (required fields, measures).
        policy: Optional severity policy (defaults to the standard policy).

    Returns:
        The flags found (may be empty).
    """
    active = policy or Policy()
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(table, schema))
    return finalize(findings, active)
