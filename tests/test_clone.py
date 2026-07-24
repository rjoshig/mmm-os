"""Tests for Phase 15 — universal clone / duplicate (CC-1/CC-10)."""

from __future__ import annotations

import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.models import (
    ConnectorConfig,
    ConnectorCredential,
    Rule,
    RuleSet,
    Tenant,
)
from mmm_os.services.clone import (
    clone_connector_config,
    clone_customer_configs,
    clone_rule_set,
)


def _session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def _tenant(session: Session) -> Tenant:
    t = Tenant(name="t", slug=f"t-{uuid.uuid4().hex[:6]}")
    session.add(t)
    session.flush()
    return t


def _rule_set(session: Session, tenant: Tenant) -> RuleSet:
    rs = RuleSet(tenant_id=tenant.id, name="std", version=1)
    session.add(rs)
    session.flush()
    session.add(
        Rule(
            tenant_id=tenant.id,
            rule_set_id=rs.id,
            target_field="channel",
            operation="lowercase",
            params={},
            order_index=0,
        )
    )
    session.flush()
    return rs


def test_clone_rule_set_deep_copies_rules(engine: Engine) -> None:
    session = _session(engine)
    tenant = _tenant(session)
    rs = _rule_set(session, tenant)

    clone = clone_rule_set(session, tenant_id=tenant.id, rule_set_id=rs.id)
    assert clone is not None
    assert clone.id != rs.id
    assert clone.name == "std (copy)"
    assert clone.lifecycle_status == "draft"
    assert clone.cloned_from == rs.id
    clone_rules = session.scalars(select_rules(clone.id)).all()
    assert len(clone_rules) == 1 and clone_rules[0].id != rs.id


def select_rules(rule_set_id: uuid.UUID):
    from sqlalchemy import select

    return select(Rule).where(Rule.rule_set_id == rule_set_id)


def test_clone_connector_never_copies_credential(engine: Engine) -> None:
    session = _session(engine)
    tenant = _tenant(session)
    cfg = ConnectorConfig(tenant_id=tenant.id, connector_key="meta", name="Meta", enabled=True)
    session.add(cfg)
    session.flush()
    session.add(
        ConnectorCredential(
            tenant_id=tenant.id, connector_config_id=cfg.id, secret_ref_name="secret://x"
        )
    )
    session.flush()

    clone = clone_connector_config(session, tenant_id=tenant.id, connector_config_id=cfg.id)
    assert clone is not None
    assert clone.enabled is False  # starts unauthenticated
    # No credential row points at the clone (CC-10).
    creds = session.scalars(
        select_creds(clone.id)
    ).all()
    assert creds == []


def select_creds(config_id: uuid.UUID):
    from sqlalchemy import select

    return select(ConnectorCredential).where(ConnectorCredential.connector_config_id == config_id)


def test_clone_customer_configs_cross_tenant(engine: Engine) -> None:
    session = _session(engine)
    src, dst = _tenant(session), _tenant(session)
    _rule_set(session, src)

    counts = clone_customer_configs(session, tenant_id=src.id, target_tenant_id=dst.id)
    assert counts["rule_sets"] == 1

    dst_rule_sets = session.scalars(
        select_rule_sets(dst.id)
    ).all()
    assert len(dst_rule_sets) == 1
    assert dst_rule_sets[0].tenant_id == dst.id  # CC-1: lands in the target tenant


def select_rule_sets(tenant_id: uuid.UUID):
    from sqlalchemy import select

    return select(RuleSet).where(RuleSet.tenant_id == tenant_id)


def test_clone_rule_set_api(client) -> None:
    tenant_id = client.post(
        "/api/v1/customers", json={"name": f"Acme {uuid.uuid4().hex[:6]}"}
    ).json()["id"]
    # Create a rule set via the transform API path is involved; instead assert the
    # clone endpoint 404s cleanly for a missing id (router + wiring smoke test).
    missing = client.post(
        f"/api/v1/tenants/{tenant_id}/rule-sets/{uuid.uuid4()}/clone", json={}
    )
    assert missing.status_code == 404
