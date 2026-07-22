"""Tenant and user services (P0.3-1).

Thin functions that create and read tenants/users. Reads are tenant-scoped via
``tenant_scoped_select`` so no operation returns cross-tenant rows (CC-1).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import Tenant, User
from mmm_os.schemas.tenant import TenantCreate, UserCreate


def create_tenant(session: Session, data: TenantCreate) -> Tenant:
    """Create a tenant.

    Args:
        session: The database session.
        data: The tenant creation payload.

    Returns:
        The persisted ``Tenant`` (flushed, with an assigned id).
    """
    tenant = Tenant(name=data.name, slug=data.slug)
    session.add(tenant)
    session.flush()
    return tenant


def create_user(session: Session, data: UserCreate) -> User:
    """Create a user scoped to a tenant.

    Args:
        session: The database session.
        data: The user creation payload (includes ``tenant_id``).

    Returns:
        The persisted ``User`` (flushed, with an assigned id).
    """
    user = User(
        tenant_id=data.tenant_id,
        email=data.email,
        display_name=data.display_name,
        role=data.role,
    )
    session.add(user)
    session.flush()
    return user


def get_user(session: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    """Fetch a user by id, scoped to a tenant.

    Args:
        session: The database session.
        tenant_id: The tenant the user must belong to.
        user_id: The user's id.

    Returns:
        The ``User`` if it exists within ``tenant_id``, else ``None`` (no
        cross-tenant access).
    """
    return session.scalar(tenant_scoped_select(User, tenant_id).where(User.id == user_id))


def list_users(session: Session, tenant_id: uuid.UUID) -> Sequence[User]:
    """List all users belonging to a tenant.

    Args:
        session: The database session.
        tenant_id: The tenant to scope to.

    Returns:
        The tenant's users (never any other tenant's).
    """
    return session.scalars(tenant_scoped_select(User, tenant_id)).all()
