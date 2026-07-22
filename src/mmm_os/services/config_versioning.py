"""Config versioning services (P0.3-2).

Saving a new revision of a ``mapping_config`` or ``rule_set`` creates a new
integer ``version`` while all prior versions are retained, so outputs stay
traceable to the exact version applied (CC-3/CC-4). Versions are numbered per
tenant + natural key (file signature for mapping configs, name for rule sets).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mmm_os.models import MappingConfig, RuleSet
from mmm_os.models.enums import RuleLayer


def _next_mapping_config_version(
    session: Session, tenant_id: uuid.UUID, file_signature: str
) -> int:
    """Return the next version number for a mapping-config natural key."""
    current = session.scalar(
        select(func.max(MappingConfig.version)).where(
            MappingConfig.tenant_id == tenant_id,
            MappingConfig.file_signature == file_signature,
        )
    )
    return (current or 0) + 1


def save_mapping_config(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    name: str,
    file_signature: str,
    mapping: dict[str, Any],
    layer: str = RuleLayer.CUSTOMER.value,
) -> MappingConfig:
    """Persist a new version of a mapping config, retaining prior versions.

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        name: Human-readable config name.
        file_signature: The column-signature key this config applies to.
        mapping: The column→canonical mapping payload.
        layer: The resolution layer (global/template/customer).

    Returns:
        The newly created ``MappingConfig`` at the next version.
    """
    config = MappingConfig(
        tenant_id=tenant_id,
        name=name,
        file_signature=file_signature,
        version=_next_mapping_config_version(session, tenant_id, file_signature),
        layer=layer,
        mapping=mapping,
    )
    session.add(config)
    session.flush()
    return config


def get_mapping_config_version(
    session: Session, tenant_id: uuid.UUID, file_signature: str, version: int
) -> MappingConfig | None:
    """Fetch a specific mapping-config version, scoped to a tenant.

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        file_signature: The column-signature key.
        version: The version number to retrieve.

    Returns:
        The matching ``MappingConfig`` or ``None``.
    """
    return session.scalar(
        select(MappingConfig).where(
            MappingConfig.tenant_id == tenant_id,
            MappingConfig.file_signature == file_signature,
            MappingConfig.version == version,
        )
    )


def _next_rule_set_version(session: Session, tenant_id: uuid.UUID, name: str) -> int:
    """Return the next version number for a rule-set natural key."""
    current = session.scalar(
        select(func.max(RuleSet.version)).where(
            RuleSet.tenant_id == tenant_id,
            RuleSet.name == name,
        )
    )
    return (current or 0) + 1


def save_rule_set(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    name: str,
    layer: str = RuleLayer.CUSTOMER.value,
) -> RuleSet:
    """Persist a new version of a rule set, retaining prior versions.

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        name: The rule-set name (natural key within the tenant).
        layer: The resolution layer (global/template/customer).

    Returns:
        The newly created ``RuleSet`` at the next version.
    """
    rule_set = RuleSet(
        tenant_id=tenant_id,
        name=name,
        version=_next_rule_set_version(session, tenant_id, name),
        layer=layer,
    )
    session.add(rule_set)
    session.flush()
    return rule_set
