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


def _seed_control_rows(store_url: str, tenant: Tenant, users: list[User]) -> None:
    """Copy a customer's tenant + user rows into its freshly provisioned silo DB.

    Business routers (routed to the silo) resolve actor emails against these rows,
    so a silo DB is self-contained. Auth/session control-plane still lives in the
    pool; post-provision user changes need a re-sync (follow-up).
    """
    from sqlalchemy.orm import Session as _Session

    engine = routing.provision_silo_database(store_url)
    with _Session(engine) as silo:
        if silo.get(Tenant, tenant.id) is None:
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
        for user in users:
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
        _seed_control_rows(body.database_url, tenant, users)
        routing.set_dedicated_database_url(store, customer_id, body.database_url)
        tenant.isolation_mode = "silo"
    else:
        routing.clear_dedicated_database_url(store, customer_id)
        tenant.isolation_mode = "pool"

    session.commit()
    routing.invalidate_tenant(customer_id)
    return CustomerRead.model_validate(tenant)
