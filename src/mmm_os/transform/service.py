"""Rule-set persistence and layered resolution (P3-5, P3-8).

A ``rule_set`` is versioned (reusing the Phase-0 helper) and owns ordered ``rule``
rows. Resolution merges the latest rule set at each layer for a name, in
precedence order global → template → customer.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.mapping.signature import column_signature
from mmm_os.models import Rule, RuleSet, Sheet
from mmm_os.services.config_versioning import save_rule_set
from mmm_os.transform.types import RuleSpec

_LAYERS = ("global", "template", "customer")


def rule_set_name_for_signature(signature: str) -> str:
    """Return the rule-set natural-key name for a column signature.

    Rule sets are reused across files with identical headers, so they are keyed by
    column signature (like mappings) rather than by ``sheet_id``. Signatures are
    usually short; a SHA-256 fallback keeps the name within the column's 255 chars
    for very wide sheets.
    """
    if len(signature) <= 240:
        return f"sig:{signature}"
    return f"sig:{hashlib.sha256(signature.encode()).hexdigest()[:16]}"


def rule_set_name_for_sheet(sheet: Sheet) -> str:
    """Return the signature-derived rule-set name for a sheet's columns."""
    return rule_set_name_for_signature(column_signature(sheet.columns))


def get_rule_set_for_sheet(
    session: Session, tenant_id: uuid.UUID, sheet: Sheet
) -> RuleSet | None:
    """Fetch the latest saved rule set matching a sheet's column signature."""
    return get_rule_set(session, tenant_id, rule_set_name_for_sheet(sheet))


def save_rule_set_with_rules(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    name: str,
    layer: str,
    specs: list[RuleSpec],
    created_by: uuid.UUID | None = None,
    lifecycle_status: str = "published",
) -> RuleSet:
    """Persist a new version of a rule set and its ordered rules.

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        name: The rule-set name (natural key within the tenant).
        layer: The resolution layer.
        specs: The ordered rule specs to persist.
        created_by: The user id authoring this version (Phase 13), if known.
        lifecycle_status: draft | published | archived (Phase 13.2).

    Returns:
        The created ``RuleSet`` at the next version.
    """
    rule_set = save_rule_set(
        session,
        tenant_id=tenant_id,
        name=name,
        layer=layer,
        created_by=created_by,
        lifecycle_status=lifecycle_status,
    )
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
    session: Session, tenant_id: uuid.UUID, name: str, layer: str, *, published_only: bool = False
) -> RuleSet | None:
    query = select(RuleSet).where(
        RuleSet.tenant_id == tenant_id, RuleSet.name == name, RuleSet.layer == layer
    )
    if published_only:
        query = query.where(RuleSet.lifecycle_status == "published")
    return session.scalar(query.order_by(RuleSet.version.desc()))


def get_rule_set(
    session: Session, tenant_id: uuid.UUID, name: str, layer: str = "customer"
) -> RuleSet | None:
    """Fetch the latest version of a named rule set (any status), for editing."""
    return _latest_rule_set(session, tenant_id, name, layer)


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
        # Pipeline resolution uses only *published* versions (Phase 13.2).
        rule_set = _latest_rule_set(session, tenant_id, name, layer, published_only=True)
        if rule_set is not None:
            specs.extend(load_rule_specs(session, rule_set))
    return specs
