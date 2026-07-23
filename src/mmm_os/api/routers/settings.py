"""Per-tenant reporting settings routes (Cycle 2): reporting currency, timezone, FX."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from mmm_os.auth.service import Principal
from mmm_os.authz import Permission, require_permission
from mmm_os.db.session import get_session
from mmm_os.governance import record_audit
from mmm_os.schemas.settings import TenantSettingsRead, TenantSettingsUpdate
from mmm_os.services.tenant_settings import get_tenant_settings, update_tenant_settings

router = APIRouter(prefix="/api/v1", tags=["settings"])

_WRITE_CONFIG = Depends(require_permission(Permission.WRITE_CONFIG))


@router.get("/tenants/{tenant_id}/settings", response_model=TenantSettingsRead)
def read_settings(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> TenantSettingsRead:
    """Return the tenant's reporting settings (creating defaults on first access)."""
    settings = get_tenant_settings(session, tenant_id)
    session.commit()
    return TenantSettingsRead.model_validate(settings)


@router.put(
    "/tenants/{tenant_id}/settings",
    response_model=TenantSettingsRead,
    status_code=status.HTTP_200_OK,
)
def write_settings(
    tenant_id: uuid.UUID,
    body: TenantSettingsUpdate,
    session: Session = Depends(get_session),
    principal: Principal | None = _WRITE_CONFIG,
) -> TenantSettingsRead:
    """Update the tenant's reporting currency / timezone / FX rates (config-as-data)."""
    settings = update_tenant_settings(
        session,
        tenant_id,
        reporting_currency=body.reporting_currency,
        reporting_timezone=body.reporting_timezone,
        fx_rates=body.fx_rates,
    )
    record_audit(
        session,
        tenant_id=tenant_id,
        action="settings.update",
        principal=principal,
        target_type="tenant_settings",
        target_id=str(settings.id),
        detail={
            "reporting_currency": settings.reporting_currency,
            "reporting_timezone": settings.reporting_timezone,
            "fx_currencies": sorted(settings.fx_rates),
        },
    )
    session.commit()
    return TenantSettingsRead.model_validate(settings)
