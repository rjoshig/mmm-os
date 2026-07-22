"""Tenant-scoping query helper.

Row-level isolation (ADR-003, CC-1) means every read must be filtered by
``tenant_id``. ``tenant_scoped_select`` makes that the default, ergonomic path so
services don't hand-roll (and forget) the filter.
"""

from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import Select, select

from mmm_os.models.mixins import TenantScopedMixin

TenantScopedT = TypeVar("TenantScopedT", bound=TenantScopedMixin)


def tenant_scoped_select(
    model: type[TenantScopedT], tenant_id: uuid.UUID
) -> Select[tuple[TenantScopedT]]:
    """Return a SELECT over ``model`` filtered to a single tenant.

    Args:
        model: A tenant-scoped ORM model class.
        tenant_id: The tenant to scope results to.

    Returns:
        A ``Select`` that yields only rows belonging to ``tenant_id``.
    """
    return select(model).where(model.tenant_id == tenant_id)
