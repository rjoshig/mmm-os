"""Connector admin/API routes (Phase 09.8): configure, sync (dev), observe.

Admin-gated (``Permission.ADMIN``). Triggering a sync uses the connector's **fake**
report client in dev (no partner credentials here); production injects a real
client. Each sync records a ``SyncRun`` (status/row counts/errors, CC-7).
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.authz import Permission, require_permission
from mmm_os.connectors.registry import CONNECTOR_KEYS, PARTNER_KEYS, build_partner_connector
from mmm_os.connectors.scheduling import incremental_window, run_sync
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.models import ConnectorConfig, SyncRun
from mmm_os.schemas.connectors import ConnectorConfigCreate, ConnectorConfigRead, SyncRunRead

router = APIRouter(prefix="/api/v1", tags=["connectors"])

_ADMIN = Depends(require_permission(Permission.ADMIN))


def _get_config(session: Session, tenant_id: uuid.UUID, config_id: uuid.UUID) -> ConnectorConfig:
    config = session.scalar(
        tenant_scoped_select(ConnectorConfig, tenant_id).where(ConnectorConfig.id == config_id)
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="connector config not found"
        )
    return config


@router.post(
    "/tenants/{tenant_id}/connector-configs",
    status_code=status.HTTP_201_CREATED,
    response_model=ConnectorConfigRead,
    dependencies=[_ADMIN],
)
def create_connector_config(
    tenant_id: uuid.UUID,
    body: ConnectorConfigCreate,
    session: Session = Depends(get_session),
) -> ConnectorConfigRead:
    """Create a per-tenant connector configuration (admin only)."""
    if body.connector_key not in CONNECTOR_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown connector_key {body.connector_key!r}",
        )
    config = ConnectorConfig(
        tenant_id=tenant_id,
        connector_key=body.connector_key,
        name=body.name,
        account_ids=body.account_ids,
        settings=body.settings,
    )
    session.add(config)
    session.commit()
    return ConnectorConfigRead.model_validate(config)


@router.get(
    "/tenants/{tenant_id}/connector-configs",
    response_model=list[ConnectorConfigRead],
    dependencies=[_ADMIN],
)
def list_connector_configs(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[ConnectorConfigRead]:
    """List a tenant's connector configurations (admin only)."""
    configs = session.scalars(
        tenant_scoped_select(ConnectorConfig, tenant_id).order_by(ConnectorConfig.created_at)
    ).all()
    return [ConnectorConfigRead.model_validate(c) for c in configs]


@router.post(
    "/tenants/{tenant_id}/connector-configs/{config_id}/sync",
    response_model=SyncRunRead,
    dependencies=[_ADMIN],
)
def trigger_sync(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> SyncRunRead:
    """Run an incremental sync now (dev: fake client) and record a SyncRun."""
    config = _get_config(session, tenant_id, config_id)
    if config.connector_key not in PARTNER_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{config.connector_key!r} is not an API partner connector",
        )
    connector = build_partner_connector(
        config.connector_key, account_ctx=config.settings.get("account_ctx", {})
    )
    result = run_sync(session, connector, config, incremental_window(config, date.today()))
    session.commit()
    return SyncRunRead.model_validate(result.sync_run)


@router.get(
    "/tenants/{tenant_id}/connector-configs/{config_id}/sync-runs",
    response_model=list[SyncRunRead],
    dependencies=[_ADMIN],
)
def list_sync_runs(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[SyncRunRead]:
    """List a config's sync runs, newest first (admin only, observability)."""
    _get_config(session, tenant_id, config_id)
    runs = session.scalars(
        tenant_scoped_select(SyncRun, tenant_id)
        .where(SyncRun.connector_config_id == config_id)
        .order_by(SyncRun.created_at.desc())
    ).all()
    return [SyncRunRead.model_validate(r) for r in runs]
