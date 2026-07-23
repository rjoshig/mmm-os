"""Tests for per-customer database engine routing (Slice 7.2)."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.db import routing
from mmm_os.db.base import Base
from mmm_os.db.routing import RoutingSession
from mmm_os.models.tenant import Tenant
from mmm_os.secrets.local import LocalEncryptedSecretStore


def _pool(tmp_path: Path) -> Session:
    """Build a pool control session with the schema created."""
    engine = create_engine(f"sqlite:///{tmp_path / 'pool.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_engine_cache_returns_same_instance(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'a.db'}"
    assert routing.get_engine(url) is routing.get_engine(url)


def test_secret_roundtrip_and_clear(tmp_path: Path) -> None:
    store = LocalEncryptedSecretStore(tmp_path / "secrets", b"k")
    tid = uuid.uuid4()
    assert routing.get_dedicated_database_url(store, tid) is None
    routing.set_dedicated_database_url(store, tid, "sqlite:///silo.db")
    assert routing.get_dedicated_database_url(store, tid) == "sqlite:///silo.db"
    routing.clear_dedicated_database_url(store, tid)
    assert routing.get_dedicated_database_url(store, tid) is None


def test_resolve_pool_for_standard_customer(tmp_path: Path) -> None:
    store = LocalEncryptedSecretStore(tmp_path / "secrets", b"k")
    session = _pool(tmp_path)
    tenant = Tenant(name="Std", slug=f"std-{uuid.uuid4().hex[:8]}")
    session.add(tenant)
    session.commit()
    routing.invalidate_tenant(tenant.id)

    engine = routing.resolve_engine_for_tenant(
        tenant.id, control_session=session, store=store
    )
    assert engine is routing.pool_engine()


def test_resolve_silo_for_enterprise_customer(tmp_path: Path) -> None:
    store = LocalEncryptedSecretStore(tmp_path / "secrets", b"k")
    session = _pool(tmp_path)
    silo_url = f"sqlite:///{tmp_path / 'silo.db'}"
    tenant = Tenant(
        name="Ent", slug=f"ent-{uuid.uuid4().hex[:8]}", tier="enterprise", isolation_mode="silo"
    )
    session.add(tenant)
    session.commit()
    routing.set_dedicated_database_url(store, tenant.id, silo_url)

    engine = routing.resolve_engine_for_tenant(
        tenant.id, control_session=session, store=store
    )
    assert engine is routing.get_engine(silo_url)
    assert engine is not routing.pool_engine()


def test_routing_session_honors_use_engine(tmp_path: Path) -> None:
    silo = routing.get_engine(f"sqlite:///{tmp_path / 'bind.db'}")
    make = sessionmaker(class_=RoutingSession)
    # Unset context -> pool engine.
    with make() as s:
        assert s.get_bind() is routing.pool_engine()
    # Bound context -> the routed engine.
    with routing.use_engine(silo), make() as s:
        assert s.get_bind() is silo
