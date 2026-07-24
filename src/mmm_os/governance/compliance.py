"""Compliance self-checks (Phase 08.1).

Programmatic controls that back the SOC 2-aligned posture: a **least-privilege**
verification over the RBAC matrix, and a **controls matrix** mapping each control
to the phase that implements it. Certification itself is an organizational process
(not code); these checks make the technical posture auditable.
"""

from __future__ import annotations

from dataclasses import dataclass

from mmm_os.authz import ROLE_PERMISSIONS, Permission


@dataclass(frozen=True)
class Control:
    """One compliance control and where it is implemented."""

    control_id: str
    description: str
    implemented_by: str


# Admin-tier roles allowed to hold ``ADMIN`` (Phase 19 adds ``platform_admin`` for
# customer/tenant management). Any role outside this set holding ADMIN is a violation.
_ADMIN_TIER_ROLES = frozenset({"admin", "platform_admin"})


def verify_least_privilege() -> list[str]:
    """Return any least-privilege violations (empty list = compliant).

    Rules: only admin-tier roles (``admin`` / ``platform_admin``) may hold
    ``ADMIN``; every role's permissions must be a subset of ``admin``'s (no role
    exceeds the superuser).
    """
    violations: list[str] = []
    admin_perms = ROLE_PERMISSIONS.get("admin", frozenset())
    for role, perms in ROLE_PERMISSIONS.items():
        if not perms <= admin_perms:
            violations.append(f"role {role!r} holds permissions outside admin's set")
        if role not in _ADMIN_TIER_ROLES and Permission.ADMIN in perms:
            violations.append(f"non-admin role {role!r} holds ADMIN")
    return violations


def controls_matrix() -> list[Control]:
    """Return the technical-controls matrix (control → implementing phase)."""
    return [
        Control("AC-1", "Authenticated access to every endpoint", "Phase 00.5 (CC-11)"),
        Control("AC-2", "Role-based least-privilege authorization", "Phase 8 (P8-1)"),
        Control("AU-1", "Audit log of sensitive actions", "Phase 8 (P8-2)"),
        Control("SC-1", "Secrets encrypted at rest, never logged", "Phase 00.6 (CC-12)"),
        Control("SC-2", "Partner credentials encrypted + tenant-scoped", "Phase 9 (CC-10)"),
        Control("CM-1", "Config/rule changes versioned + attributable", "Phases 2/3 + 8 (CC-4)"),
        Control("SI-1", "Idempotent, retry-safe processing", "Phases 1/7.2 (CC-6)"),
        Control("AU-2", "Per-job event timeline + metrics", "Phases 1/7.1 (CC-7)"),
        Control("DI-1", "Row-level tenant isolation", "Phase 0/7 (CC-1)"),
    ]
