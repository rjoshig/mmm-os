"""Integration tests for silo isolation hardening (Slice 7.6).

Verify that the background scheduler routes each silo customer's due syncs to its
own database (never the pool), and that control-plane user rows are mirrored into a
silo so routed look-ups stay self-contained.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.connectors.autoschedule import run_all_due_syncs
from mmm_os.db import routing
from mmm_os.db.base import Base
from mmm_os.db.silo_sync import mirror_user_to_silo
from mmm_os.models import ConnectorConfig, SyncRun, Tenant, User
from mmm_os.secrets.local import LocalEncryptedSecretStore

_SCHEDULE = {"schedule": {"interval_minutes": 60}}


def _make_db(path: Path, name: str) -> Session:
    engine = create_engine(f"sqlite:///{path / name}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _scheduled_config(tenant_id: uuid.UUID, name: str) -> ConnectorConfig:
    return ConnectorConfig(
        tenant_id=tenant_id,
        connector_key="meta",
        name=name,
        account_ids=["act_1"],
        settings=_SCHEDULE,
    )


def test_scheduler_routes_silo_sync_to_its_own_db(tmp_path: Path) -> None:
    store = LocalEncryptedSecretStore(tmp_path / "secrets", b"k")
    pool = _make_db(tmp_path, "pool.db")
    silo_url = f"sqlite:///{tmp_path / 'silo.db'}"
    routing.provision_silo_database(silo_url)

    # A pool-tier customer with a scheduled config (lives in the pool DB).
    pool_tenant = Tenant(name="Std", slug=f"std-{uuid.uuid4().hex[:6]}")
    pool.add(pool_tenant)
    pool.flush()
    pool.add(_scheduled_config(pool_tenant.id, "pool-meta"))

    # A silo-tier customer; its config lives ONLY in the silo DB.
    silo_tenant = Tenant(
        name="Ent", slug=f"ent-{uuid.uuid4().hex[:6]}", tier="enterprise", isolation_mode="silo"
    )
    pool.add(silo_tenant)
    pool.flush()
    routing.set_dedicated_database_url(store, silo_tenant.id, silo_url)
    pool.commit()

    silo_engine = routing.get_engine(silo_url)
    with Session(silo_engine) as silo:
        silo.add(_scheduled_config(silo_tenant.id, "silo-meta"))
        silo.commit()

    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    results = run_all_due_syncs(pool, store, now)
    assert len(results) == 2  # both customers' configs were due

    # The silo customer's SyncRun landed in the silo DB, not the pool.
    with Session(silo_engine) as silo:
        silo_runs = silo.scalars(select(SyncRun)).all()
        assert len(silo_runs) == 1
        assert silo_runs[0].tenant_id == silo_tenant.id

    pool_runs = pool.scalars(select(SyncRun)).all()
    assert [r.tenant_id for r in pool_runs] == [pool_tenant.id]


def test_mirror_user_noop_for_pool_tenant(tmp_path: Path) -> None:
    store = LocalEncryptedSecretStore(tmp_path / "secrets", b"k")
    user = User(id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="x@x.example")
    # No dedicated URL for this tenant -> silent no-op (must not raise).
    mirror_user_to_silo(store, user)


def test_mirror_user_upserts_into_silo(tmp_path: Path) -> None:
    store = LocalEncryptedSecretStore(tmp_path / "secrets", b"k")
    silo_url = f"sqlite:///{tmp_path / 'silo.db'}"
    routing.provision_silo_database(silo_url)
    tenant_id = uuid.uuid4()
    routing.set_dedicated_database_url(store, tenant_id, silo_url)

    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email="ops@ent.example", role="admin")
    mirror_user_to_silo(store, user)

    with Session(routing.get_engine(silo_url)) as silo:
        got = silo.get(User, user.id)
        assert got is not None and got.email == "ops@ent.example"
