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

from mmm_os.authz import Permission, require_permission
from mmm_os.db.session import get_session
from mmm_os.models import Tenant
from mmm_os.schemas.customer import CustomerCreate, CustomerRead

router = APIRouter(prefix="/api/v1", tags=["customers"])

_ADMIN = Depends(require_permission(Permission.ADMIN))

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """Return a url-safe slug derived from ``value``."""
    return _SLUG_STRIP.sub("-", value.strip().lower()).strip("-") or "customer"


@router.get("/customers", response_model=list[CustomerRead], dependencies=[_ADMIN])
def list_customers(session: Session = Depends(get_session)) -> list[CustomerRead]:
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
    session: Session = Depends(get_session),
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
    session: Session = Depends(get_session),
) -> CustomerRead:
    """Return one customer / workspace."""
    tenant = session.scalar(select(Tenant).where(Tenant.id == customer_id))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer not found")
    return CustomerRead.model_validate(tenant)
