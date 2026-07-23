"""Connector admin/API routes (Phase 09.8): configure, sync (dev), observe.

Admin-gated (``Permission.ADMIN``). Triggering a sync uses the connector's **fake**
report client in dev (no partner credentials here); production injects a real
client. Each sync records a ``SyncRun`` (status/row counts/errors, CC-7).
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.api.deps import get_secret_store_dep
from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.connectors.autoschedule import run_due_syncs
from mmm_os.connectors.credentials import store_token
from mmm_os.connectors.registry import CONNECTOR_KEYS, PARTNER_KEYS, build_partner_connector
from mmm_os.connectors.scheduling import incremental_window, run_sync
from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.db.session import get_session
from mmm_os.models import ConnectorConfig, ConnectorCredential, SyncRun, User
from mmm_os.models.mixins import utcnow
from mmm_os.schemas.connectors import (
    ConnectorConfigCreate,
    ConnectorConfigRead,
    ConnectorCredentialInput,
    ConnectorCredentialStatus,
    RunDueResponse,
    ScheduleUpdate,
    SyncRunListItem,
    SyncRunRead,
)
from mmm_os.secrets import SecretStore

router = APIRouter(prefix="/api/v1", tags=["connectors"])

_ADMIN = Depends(require_permission(Permission.ADMIN))


def _credential_for(session: Session, config_id: uuid.UUID) -> ConnectorCredential | None:
    """Return the stored credential reference for a connector config, if any."""
    return session.scalar(
        select(ConnectorCredential).where(
            ConnectorCredential.connector_config_id == config_id
        )
    )


def _read_config(session: Session, config: ConnectorConfig) -> ConnectorConfigRead:
    """Build a ConnectorConfigRead enriched with (non-secret) credential status."""
    read = ConnectorConfigRead.model_validate(config)
    credential = _credential_for(session, config.id)
    if credential is not None:
        read.has_credential = True
        read.credential_scopes = credential.scopes
        read.credential_expires_at = credential.expires_at
    return read


@router.get("/connectors/available", dependencies=[_ADMIN])
def list_available_connectors() -> dict[str, list[dict[str, object]]]:
    """List the connector keys the platform supports (for the create-source form).

    Partner connectors (``is_partner``) support triggering a sync; ``sftp`` is a file
    source. Not tenant-scoped — the catalog is the same for every tenant.
    """
    connectors = [
        {"key": key, "is_partner": key in PARTNER_KEYS} for key in sorted(CONNECTOR_KEYS)
    ]
    return {"connectors": connectors}


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
    return _read_config(session, config)


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
    return [_read_config(session, c) for c in configs]


@router.put(
    "/tenants/{tenant_id}/connector-configs/{config_id}/credential",
    response_model=ConnectorCredentialStatus,
    dependencies=[_ADMIN],
)
def set_connector_credential(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    body: ConnectorCredentialInput,
    session: Session = Depends(get_session),
    store: SecretStore = Depends(get_secret_store_dep),
) -> ConnectorCredentialStatus:
    """Store (or replace) a partner token for a connector (CC-10/CC-12).

    The token is encrypted in the ``SecretStore`` and never returned or logged; the
    database keeps only a reference. Only partner connectors take credentials.

    Raises:
        HTTPException: 404 if unknown, 400 for a non-partner (file) connector.
    """
    config = _get_config(session, tenant_id, config_id)
    if config.connector_key not in PARTNER_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="only partner connectors take credentials",
        )
    credential = store_token(
        session,
        store,
        tenant_id=tenant_id,
        connector_config_id=config_id,
        token=body.token,
        scopes=body.scopes,
        expires_at=body.expires_at,
    )
    session.commit()
    return ConnectorCredentialStatus(
        has_credential=True,
        scopes=credential.scopes,
        expires_at=credential.expires_at,
    )


@router.get(
    "/tenants/{tenant_id}/connector-configs/{config_id}/credential",
    response_model=ConnectorCredentialStatus,
    dependencies=[_ADMIN],
)
def get_connector_credential(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ConnectorCredentialStatus:
    """Return whether a connector has a stored credential (never the token)."""
    _get_config(session, tenant_id, config_id)
    credential = _credential_for(session, config_id)
    if credential is None:
        return ConnectorCredentialStatus(has_credential=False)
    return ConnectorCredentialStatus(
        has_credential=True, scopes=credential.scopes, expires_at=credential.expires_at
    )


@router.delete(
    "/tenants/{tenant_id}/connector-configs/{config_id}/credential",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ADMIN],
)
def delete_connector_credential(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    session: Session = Depends(get_session),
    store: SecretStore = Depends(get_secret_store_dep),
) -> None:
    """Remove a connector's stored credential + its secret (CC-10)."""
    _get_config(session, tenant_id, config_id)
    credential = _credential_for(session, config_id)
    if credential is not None:
        store.delete(credential.secret_ref_name)
        session.delete(credential)
        session.commit()


@router.post(
    "/tenants/{tenant_id}/connector-configs/{config_id}/sync",
    response_model=SyncRunRead,
    dependencies=[_ADMIN],
)
def trigger_sync(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    session: Session = Depends(get_session),
    principal: Principal | None = _ADMIN,
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
    result = run_sync(
        session,
        connector,
        config,
        incremental_window(config, date.today()),
        created_by=principal.user_id if principal else None,
    )
    session.commit()
    return SyncRunRead.model_validate(result.sync_run)


@router.get(
    "/tenants/{tenant_id}/sync-runs",
    response_model=list[SyncRunListItem],
    dependencies=[_ADMIN],
)
def list_all_sync_runs(
    tenant_id: uuid.UUID,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[SyncRunListItem]:
    """List a tenant's sync runs across all connectors, newest first (Runs view)."""
    configs = {
        c.id: c
        for c in session.scalars(tenant_scoped_select(ConnectorConfig, tenant_id)).all()
    }
    emails = {
        u.id: u.email for u in session.scalars(tenant_scoped_select(User, tenant_id)).all()
    }
    runs = session.scalars(
        tenant_scoped_select(SyncRun, tenant_id).order_by(SyncRun.created_at.desc()).limit(limit)
    ).all()
    items: list[SyncRunListItem] = []
    for run in runs:
        config = configs.get(run.connector_config_id)
        items.append(
            SyncRunListItem(
                run=SyncRunRead.model_validate(run),
                connector_key=config.connector_key if config else "unknown",
                connector_name=config.name if config else "(deleted)",
                triggered_by_email=emails.get(run.created_by) if run.created_by else None,
            )
        )
    return items


@router.put(
    "/tenants/{tenant_id}/connector-configs/{config_id}/schedule",
    response_model=ConnectorConfigRead,
    dependencies=[_ADMIN],
)
def set_schedule(
    tenant_id: uuid.UUID,
    config_id: uuid.UUID,
    body: ScheduleUpdate,
    session: Session = Depends(get_session),
) -> ConnectorConfigRead:
    """Set or clear a connector's automatic schedule (``interval_minutes``).

    Stored in ``settings.schedule`` (config-as-data). The scheduler runs an
    incremental sync every interval once its previous run is that old.
    """
    config = _get_config(session, tenant_id, config_id)
    settings = dict(config.settings)
    if body.interval_minutes and body.interval_minutes > 0:
        settings["schedule"] = {"interval_minutes": int(body.interval_minutes)}
    else:
        settings.pop("schedule", None)
    config.settings = settings
    session.commit()
    return ConnectorConfigRead.model_validate(config)


@router.post(
    "/tenants/{tenant_id}/scheduler/run-due",
    response_model=RunDueResponse,
    dependencies=[_ADMIN],
)
def run_due(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> RunDueResponse:
    """Run any due scheduled syncs for this tenant now (manual trigger).

    Same code path as the background scheduler — useful to demonstrate or force a
    scheduled run without waiting for the timer.
    """
    results = run_due_syncs(session, utcnow(), tenant_id=tenant_id)
    session.commit()
    return RunDueResponse(ran=[SyncRunRead.model_validate(r.sync_run) for r in results])


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
