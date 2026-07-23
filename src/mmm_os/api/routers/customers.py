"""Customer / workspace management routes (Cycle 7, Slice 7.1).

Platform-level (NOT tenant-scoped): list + onboard customers. Admin-gated (in dev,
auth off makes this a no-op). A tenant *is* a customer/workspace — the isolation root
(CC-1); every other route stays tenant-scoped.

Note: a dedicated platform-admin role is a follow-up; today this reuses the ADMIN
permission on the acting principal.
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_secret_store_dep
from mmm_os.authz import Permission, require_permission
from mmm_os.db import routing
from mmm_os.db.session import get_control_session
from mmm_os.db.silo_sync import mirror_tenant_to_silo, mirror_user_to_silo
from mmm_os.models import Tenant, User
from mmm_os.schemas.customer import CustomerCreate, CustomerIsolationUpdate, CustomerRead
from mmm_os.secrets import SecretStore

router = APIRouter(prefix="/api/v1", tags=["customers"])

_ADMIN = Depends(require_permission(Permission.ADMIN))

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """Return a url-safe slug derived from ``value``."""
    return _SLUG_STRIP.sub("-", value.strip().lower()).strip("-") or "customer"


@router.get("/customers", response_model=list[CustomerRead], dependencies=[_ADMIN])
def list_customers(session: Session = Depends(get_control_session)) -> list[CustomerRead]:
    """List all customer workspaces, newest first (workspace switcher + admin)."""
    tenants = session.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()
    return [CustomerRead.model_validate(t) for t in tenants]


@router.post(
    "/customers",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
def create_customer(
    body: CustomerCreate,
    session: Session = Depends(get_control_session),
) -> CustomerRead:
    """Onboard a new customer / workspace (the isolation root).

    Raises:
        HTTPException: 409 if the slug is already taken.
    """
    slug = _slugify(body.slug or body.name)
    if session.scalar(select(Tenant).where(Tenant.slug == slug)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"slug {slug!r} already exists"
        )
    tenant = Tenant(name=body.name, slug=slug, tier=body.tier, region=body.region)
    session.add(tenant)
    session.commit()
    return CustomerRead.model_validate(tenant)


@router.get("/customers/{customer_id}", response_model=CustomerRead, dependencies=[_ADMIN])
def get_customer(
    customer_id: uuid.UUID,
    session: Session = Depends(get_control_session),
) -> CustomerRead:
    """Return one customer / workspace."""
    tenant = session.scalar(select(Tenant).where(Tenant.id == customer_id))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer not found")
    return CustomerRead.model_validate(tenant)


def _seed_control_rows(
    store: SecretStore, store_url: str, tenant: Tenant, users: list[User]
) -> None:
    """Provision the silo schema and seed the customer's tenant + user rows.

    Business routers (routed to the silo) resolve actor emails against these rows,
    so a silo DB is self-contained. Ongoing changes are re-mirrored by
    ``db/silo_sync.py`` from control-plane write paths.
    """
    routing.provision_silo_database(store_url)
    mirror_tenant_to_silo(store, tenant)
    for user in users:
        mirror_user_to_silo(store, user)


@router.put(
    "/customers/{customer_id}/isolation",
    response_model=CustomerRead,
    dependencies=[_ADMIN],
)
def set_customer_isolation(
    customer_id: uuid.UUID,
    body: CustomerIsolationUpdate,
    session: Session = Depends(get_control_session),
    store: SecretStore = Depends(get_secret_store_dep),
) -> CustomerRead:
    """Move a customer between the shared pool and a dedicated silo database (7.2).

    Silo requires an enterprise-tier customer + a ``database_url``; the URL is stored
    in the SecretStore (CC-12) and the dedicated schema is provisioned. Returning to
    pool clears the stored URL. Routing itself is gated by ``multi_db_routing_enabled``.

    Raises:
        HTTPException: 404 if unknown, 400 if silo requested without a URL or for a
            non-enterprise customer.
    """
    tenant = session.get(Tenant, customer_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer not found")

    if body.mode == "silo":
        if not body.database_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="database_url is required for silo isolation",
            )
        if tenant.tier != "enterprise":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="silo isolation requires an enterprise-tier customer",
            )
        users = list(session.scalars(select(User).where(User.tenant_id == customer_id)).all())
        # Register the URL first so the silo-sync mirrors can resolve the engine.
        routing.set_dedicated_database_url(store, customer_id, body.database_url)
        tenant.isolation_mode = "silo"
        _seed_control_rows(store, body.database_url, tenant, users)
    else:
        routing.clear_dedicated_database_url(store, customer_id)
        tenant.isolation_mode = "pool"

    session.commit()
    routing.invalidate_tenant(customer_id)
    return CustomerRead.model_validate(tenant)
