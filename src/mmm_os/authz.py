"""Role-based access control (Phase 8, P8-1 / P8-4).

A small, explicit role→permission matrix plus a ``require_permission`` dependency
factory. Access is **deny-by-default**: a role only gets the permissions listed
for it. The matrix is intentionally least-privilege (a self-check in Phase 08.1
verifies no role exceeds ``admin``).
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from fastapi import Depends, HTTPException, status

from mmm_os.auth.service import Principal


class Permission(str, Enum):
    """Discrete actions a role may be granted."""

    READ = "read"  # view files, mappings, flags, suggestions
    WRITE_CONFIG = "write_config"  # save mappings / rule sets
    REVIEW = "review"  # accept/reject suggestions; resolve flags
    ADMIN = "admin"  # manage users, view audit log


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "admin": frozenset(Permission),
    "member": frozenset({Permission.READ, Permission.WRITE_CONFIG, Permission.REVIEW}),
    "viewer": frozenset({Permission.READ}),
}


def has_permission(role: str, permission: Permission) -> bool:
    """Return whether ``role`` is granted ``permission`` (unknown roles get none)."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def require_permission(
    permission: Permission,
) -> Callable[..., Principal | None]:
    """Build a dependency enforcing ``permission`` on the authenticated principal.

    When auth is disabled (dev/tests default), ``require_auth`` yields ``None`` and
    access is allowed. When enabled, the principal's role must grant the
    permission, else 403.
    """
    # Imported here to avoid a circular import (deps -> authz -> deps).
    from mmm_os.api.deps import require_auth

    def _dep(principal: Principal | None = Depends(require_auth)) -> Principal | None:
        if principal is None:
            return None
        if not has_permission(principal.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role {principal.role!r} lacks permission {permission.value!r}",
            )
        return principal

    return _dep
