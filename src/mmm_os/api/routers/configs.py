"""Config-library routes (Phase 13, Slice 1): browse saved configs + authorship.

Read-only views over the versioned mapping configs + rule sets a tenant's team owns,
so collaborators can see what exists, who authored each version, and the history.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.models import MappingConfig, Rule, RuleSet, User
from mmm_os.schemas.config_library import (
    ConfigLibraryItem,
    ConfigLibraryResponse,
    ConfigVersionItem,
    ConfigVersionsResponse,
)

router = APIRouter(prefix="/api/v1", tags=["config-library"])


def _emails(session: Session, tenant_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """Map user id → email for the tenant (author display)."""
    users = session.scalars(tenant_scoped_select(User, tenant_id)).all()
    return {u.id: u.email for u in users}


@router.get("/tenants/{tenant_id}/config-library", response_model=ConfigLibraryResponse)
def config_library(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ConfigLibraryResponse:
    """List the tenant's saved mapping configs + rule sets, one entry per family."""
    emails = _emails(session, tenant_id)
    items: list[ConfigLibraryItem] = []

    mappings = session.scalars(tenant_scoped_select(MappingConfig, tenant_id)).all()
    by_sig: dict[str, list[MappingConfig]] = {}
    for m in mappings:
        by_sig.setdefault(m.file_signature, []).append(m)
    for signature, versions in by_sig.items():
        latest = max(versions, key=lambda c: c.version)
        items.append(
            ConfigLibraryItem(
                kind="mapping",
                key=signature,
                name=latest.name,
                layer=latest.layer,
                latest_version=latest.version,
                version_count=len(versions),
                updated_at=latest.updated_at,
                created_by_email=emails.get(latest.created_by) if latest.created_by else None,
            )
        )

    rule_sets = session.scalars(tenant_scoped_select(RuleSet, tenant_id)).all()
    by_name: dict[str, list[RuleSet]] = {}
    for r in rule_sets:
        by_name.setdefault(r.name, []).append(r)
    for name, rs_versions in by_name.items():
        rs_latest = max(rs_versions, key=lambda c: c.version)
        items.append(
            ConfigLibraryItem(
                kind="rule_set",
                key=name,
                name=name,
                layer=rs_latest.layer,
                latest_version=rs_latest.version,
                version_count=len(rs_versions),
                updated_at=rs_latest.updated_at,
                created_by_email=emails.get(rs_latest.created_by) if rs_latest.created_by else None,
            )
        )

    items.sort(key=lambda i: i.updated_at, reverse=True)
    return ConfigLibraryResponse(items=items)


@router.get(
    "/tenants/{tenant_id}/config-library/versions",
    response_model=ConfigVersionsResponse,
)
def config_versions(
    tenant_id: uuid.UUID,
    kind: str,
    key: str,
    session: Session = Depends(get_session),
) -> ConfigVersionsResponse:
    """Return the version history of one config family (mapping signature or rule-set name)."""
    emails = _emails(session, tenant_id)
    versions: list[ConfigVersionItem] = []

    if kind == "mapping":
        rows = session.scalars(
            tenant_scoped_select(MappingConfig, tenant_id).where(
                MappingConfig.file_signature == key
            )
        ).all()
        for m in sorted(rows, key=lambda c: c.version, reverse=True):
            columns = m.mapping.get("columns", {}) if isinstance(m.mapping, dict) else {}
            mapped = sum(1 for v in columns.values() if v)
            versions.append(
                ConfigVersionItem(
                    version=m.version,
                    layer=m.layer,
                    created_at=m.created_at,
                    created_by_email=emails.get(m.created_by) if m.created_by else None,
                    summary=f"{mapped} columns mapped",
                )
            )
    elif kind == "rule_set":
        rs_rows = session.scalars(
            tenant_scoped_select(RuleSet, tenant_id).where(RuleSet.name == key)
        ).all()
        for rs in sorted(rs_rows, key=lambda c: c.version, reverse=True):
            count = len(
                session.scalars(
                    tenant_scoped_select(Rule, tenant_id).where(Rule.rule_set_id == rs.id)
                ).all()
            )
            versions.append(
                ConfigVersionItem(
                    version=rs.version,
                    layer=rs.layer,
                    created_at=rs.created_at,
                    created_by_email=emails.get(rs.created_by) if rs.created_by else None,
                    summary=f"{count} rules",
                )
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown kind {kind!r}"
        )

    if not versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="config not found")
    return ConfigVersionsResponse(kind=kind, key=key, versions=versions)
