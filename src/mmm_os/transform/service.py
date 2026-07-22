"""Rule-set persistence and layered resolution (P3-5, P3-8).

A ``rule_set`` is versioned (reusing the Phase-0 helper) and owns ordered ``rule``
rows. Resolution merges the latest rule set at each layer for a name, in
precedence order global → template → customer.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.models import Rule, RuleSet
from mmm_os.services.config_versioning import save_rule_set
from mmm_os.transform.types import RuleSpec

_LAYERS = ("global", "template", "customer")


def save_rule_set_with_rules(
    session: Session, *, tenant_id: uuid.UUID, name: str, layer: str, specs: list[RuleSpec]
) -> RuleSet:
    """Persist a new version of a rule set and its ordered rules.

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        name: The rule-set name (natural key within the tenant).
        layer: The resolution layer.
        specs: The ordered rule specs to persist.

    Returns:
        The created ``RuleSet`` at the next version.
    """
    rule_set = save_rule_set(session, tenant_id=tenant_id, name=name, layer=layer)
    for spec in specs:
        session.add(
            Rule(
                tenant_id=tenant_id,
                rule_set_id=rule_set.id,
                target_field=spec.target_field,
                operation=spec.operation,
                params=spec.params,
                condition=spec.condition,
                order_index=spec.order,
                layer=spec.layer,
            )
        )
    session.flush()
    return rule_set


def load_rule_specs(session: Session, rule_set: RuleSet) -> list[RuleSpec]:
    """Load a rule set's rules as ``RuleSpec`` objects, ordered by ``order_index``."""
    rules = session.scalars(
        select(Rule).where(Rule.rule_set_id == rule_set.id).order_by(Rule.order_index)
    ).all()
    return [
        RuleSpec(
            target_field=rule.target_field,
            operation=rule.operation,
            params=rule.params,
            condition=rule.condition,
            order=rule.order_index,
            layer=rule.layer,
        )
        for rule in rules
    ]


def _latest_rule_set(
    session: Session, tenant_id: uuid.UUID, name: str, layer: str
) -> RuleSet | None:
    return session.scalar(
        select(RuleSet)
        .where(RuleSet.tenant_id == tenant_id, RuleSet.name == name, RuleSet.layer == layer)
        .order_by(RuleSet.version.desc())
    )


def resolve_rule_specs(session: Session, tenant_id: uuid.UUID, name: str) -> list[RuleSpec]:
    """Merge the latest rule set at each layer for a name (global→customer).

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        name: The rule-set name to resolve.

    Returns:
        The concatenated rule specs across layers (empty if none).
    """
    specs: list[RuleSpec] = []
    for layer in _LAYERS:
        rule_set = _latest_rule_set(session, tenant_id, name, layer)
        if rule_set is not None:
            specs.extend(load_rule_specs(session, rule_set))
    return specs
