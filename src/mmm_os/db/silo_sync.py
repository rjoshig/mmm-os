"""Mirror control-plane rows into a customer's silo database (Slice 7.6).

Auth/session control-plane always lives in the pool (see ``get_control_session``),
but a silo customer's *business* queries route to its dedicated database — and some
of those join to the customer's tenant + user rows (e.g. resolving the actor email
on a job/sync). So when a control-plane tenant or user is created or updated, mirror
it into the silo so routed look-ups stay self-contained.

A tenant is "silo" iff a dedicated DB URL is stored for it; these helpers are no-ops
otherwise, so they are safe to call unconditionally from control-plane write paths.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from mmm_os.db import routing
from mmm_os.models import Tenant, User
from mmm_os.secrets import SecretStore


def _silo_session(store: SecretStore, tenant_id: uuid.UUID) -> Session | None:
    url = routing.get_dedicated_database_url(store, tenant_id)
    if not url:
        return None
    return Session(routing.get_engine(url))


def mirror_tenant_to_silo(store: SecretStore, tenant: Tenant) -> None:
    """Upsert a tenant row into its silo DB (no-op if the tenant is pool-tier)."""
    silo = _silo_session(store, tenant.id)
    if silo is None:
        return
    with silo:
        silo.merge(
            Tenant(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                tier=tenant.tier,
                region=tenant.region,
                status=tenant.status,
                isolation_mode="silo",
            )
        )
        silo.commit()


def mirror_user_to_silo(store: SecretStore, user: User) -> None:
    """Upsert a user row into its tenant's silo DB (no-op if the tenant is pool-tier)."""
    silo = _silo_session(store, user.tenant_id)
    if silo is None:
        return
    with silo:
        silo.merge(
            User(
                id=user.id,
                tenant_id=user.tenant_id,
                email=user.email,
                display_name=user.display_name,
                role=user.role,
                status=user.status,
            )
        )
        silo.commit()
