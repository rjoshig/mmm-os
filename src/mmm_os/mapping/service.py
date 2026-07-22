"""Saved mapping configs: persistence, layered resolution, and auto-mapping (02.2).

Mappings are stored on ``mapping_config.mapping`` as ``{"columns": {source: field}}``,
keyed by tenant + column signature and versioned (reusing the Phase-0 helper).
Resolution merges the latest active config at each layer in precedence order
**customer > template > global** (P2-4).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.canonical.models import CanonicalSchema
from mmm_os.mapping.engine import MappingResult, apply_mapping
from mmm_os.mapping.signature import column_signature
from mmm_os.models import MappingConfig, Sheet
from mmm_os.models.enums import RuleLayer
from mmm_os.services.config_versioning import save_mapping_config

# Applied global first so later (customer) layers override earlier ones.
_LAYER_ORDER = (RuleLayer.GLOBAL.value, RuleLayer.TEMPLATE.value, RuleLayer.CUSTOMER.value)


@dataclass(frozen=True)
class AutoMapResult:
    """Result of attempting to auto-apply a saved config to a sheet."""

    signature: str
    matched: bool
    mapping: dict[str, str | None]
    result: MappingResult | None


def save_sheet_mapping(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    sheet: Sheet,
    name: str,
    mapping: dict[str, str | None],
    layer: str = RuleLayer.CUSTOMER.value,
) -> MappingConfig:
    """Persist a new version of a mapping for a sheet's column signature.

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        sheet: The sheet whose signature keys the config.
        name: Human-readable config name.
        mapping: ``{source_name: canonical_field | None}``.
        layer: The resolution layer (global/template/customer).

    Returns:
        The newly created ``MappingConfig`` at the next version.
    """
    signature = column_signature(sheet.columns)
    return save_mapping_config(
        session,
        tenant_id=tenant_id,
        name=name,
        file_signature=signature,
        mapping={"columns": mapping},
        layer=layer,
    )


def _latest_config(
    session: Session, tenant_id: uuid.UUID, signature: str, layer: str
) -> MappingConfig | None:
    return session.scalar(
        select(MappingConfig)
        .where(
            MappingConfig.tenant_id == tenant_id,
            MappingConfig.file_signature == signature,
            MappingConfig.layer == layer,
            MappingConfig.is_active.is_(True),
        )
        .order_by(MappingConfig.version.desc())
    )


def resolve_mapping(
    session: Session, tenant_id: uuid.UUID, signature: str
) -> dict[str, str | None]:
    """Merge the latest config at each layer for a signature (customer wins).

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        signature: The column signature to resolve.

    Returns:
        The merged ``{source_name: canonical_field | None}`` mapping (empty if none).
    """
    merged: dict[str, str | None] = {}
    for layer in _LAYER_ORDER:
        config = _latest_config(session, tenant_id, signature, layer)
        if config is not None:
            columns: dict[str, str | None] = config.mapping.get("columns", {})
            merged.update(columns)
    return merged


def auto_map_sheet(
    session: Session, tenant_id: uuid.UUID, sheet: Sheet, schema: CanonicalSchema
) -> AutoMapResult:
    """Attempt to auto-apply a saved mapping to a sheet by its signature (P2-3).

    Args:
        session: The database session.
        tenant_id: The owning tenant.
        sheet: The sheet to map.
        schema: The canonical schema (for validation).

    Returns:
        An ``AutoMapResult``; ``matched`` is ``False`` when no config exists
        (the sheet needs mapping).
    """
    signature = column_signature(sheet.columns)
    merged = resolve_mapping(session, tenant_id, signature)
    if not merged:
        return AutoMapResult(signature=signature, matched=False, mapping={}, result=None)
    result = apply_mapping(sheet.columns, merged, schema)
    return AutoMapResult(signature=signature, matched=True, mapping=merged, result=result)
