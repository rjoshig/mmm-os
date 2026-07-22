"""Tests for Phase 0.3 tenancy services and config versioning."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mmm_os.db.base import Base
from mmm_os.schemas.tenant import TenantCreate, UserCreate
from mmm_os.services.config_versioning import (
    get_mapping_config_version,
    save_mapping_config,
    save_rule_set,
)
from mmm_os.services.tenancy import create_tenant, create_user, get_user, list_users


@pytest.fixture
def session() -> Iterator[Session]:
    """Yield a session on a fresh in-memory database with all tables created."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_tenant_and_scoped_user(session: Session) -> None:
    """A tenant and a tenant-scoped user can be created and read back."""
    tenant = create_tenant(session, TenantCreate(name="Acme", slug="acme"))
    user = create_user(
        session, UserCreate(tenant_id=tenant.id, email="ada@acme.example", display_name="Ada")
    )
    session.commit()

    fetched = get_user(session, tenant.id, user.id)
    assert fetched is not None
    assert fetched.tenant_id == tenant.id
    assert fetched.role == "member"


def test_reads_are_tenant_scoped(session: Session) -> None:
    """A user is never visible from another tenant (CC-1)."""
    tenant_a = create_tenant(session, TenantCreate(name="A", slug="a"))
    tenant_b = create_tenant(session, TenantCreate(name="B", slug="b"))
    user_a = create_user(session, UserCreate(tenant_id=tenant_a.id, email="a@a.example"))
    session.commit()

    # Same user id, wrong tenant → not found.
    assert get_user(session, tenant_b.id, user_a.id) is None
    # Tenant B sees no users; tenant A sees exactly one.
    assert list(list_users(session, tenant_b.id)) == []
    assert [u.id for u in list_users(session, tenant_a.id)] == [user_a.id]


def test_mapping_config_versioning_retains_prior(session: Session) -> None:
    """Saving a config twice yields v1 then v2, with v1 still retrievable."""
    tenant = create_tenant(session, TenantCreate(name="Acme", slug="acme"))
    sig = "date|channel|spend"

    v1 = save_mapping_config(
        session,
        tenant_id=tenant.id,
        name="meta-export",
        file_signature=sig,
        mapping={"Spend": "spend"},
    )
    v2 = save_mapping_config(
        session,
        tenant_id=tenant.id,
        name="meta-export",
        file_signature=sig,
        mapping={"Spend": "spend", "Chan": "channel"},
    )
    session.commit()

    assert v1.version == 1
    assert v2.version == 2

    # v1 remains retrievable and unchanged (traceability).
    fetched_v1 = get_mapping_config_version(session, tenant.id, sig, 1)
    assert fetched_v1 is not None
    assert fetched_v1.mapping == {"Spend": "spend"}


def test_config_versioning_is_per_tenant(session: Session) -> None:
    """Version numbering restarts per tenant for the same signature."""
    tenant_a = create_tenant(session, TenantCreate(name="A", slug="a"))
    tenant_b = create_tenant(session, TenantCreate(name="B", slug="b"))
    sig = "date|channel"

    a1 = save_mapping_config(
        session, tenant_id=tenant_a.id, name="x", file_signature=sig, mapping={}
    )
    b1 = save_mapping_config(
        session, tenant_id=tenant_b.id, name="x", file_signature=sig, mapping={}
    )
    session.commit()

    assert a1.version == 1
    assert b1.version == 1


def test_rule_set_versioning(session: Session) -> None:
    """Saving a rule set twice yields versions 1 then 2."""
    tenant = create_tenant(session, TenantCreate(name="Acme", slug="acme"))
    rs1 = save_rule_set(session, tenant_id=tenant.id, name="defaults")
    rs2 = save_rule_set(session, tenant_id=tenant.id, name="defaults")
    session.commit()

    assert (rs1.version, rs2.version) == (1, 2)
