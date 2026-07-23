"""Per-tenant reporting settings (Cycle 2): reporting currency, timezone, FX rates.

Config-as-data (CC-4): these drive currency/timezone normalization so every tenant's
output lands in one consistent reporting frame. Read into the transform ``RuleContext``
so ``convert_currency`` / ``normalize_timezone`` can resolve the reporting frame.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from mmm_os.db.scoping import tenant_scoped_select
from mmm_os.models import TenantSettings
from mmm_os.transform.registry import ReportingContext


def reporting_context(session: Session, tenant_id: uuid.UUID) -> ReportingContext:
    """Build the transform ``ReportingContext`` from a tenant's settings (read-only).

    Returns defaults (USD / UTC / no FX) when the tenant has no settings row yet —
    without creating one, so read paths (preview/validation/output) stay side-effect
    free.
    """
    settings = session.scalar(tenant_scoped_select(TenantSettings, tenant_id))
    if settings is None:
        return ReportingContext()
    return ReportingContext(
        currency=settings.reporting_currency,
        timezone=settings.reporting_timezone,
        fx_rates={str(k): float(v) for k, v in settings.fx_rates.items()},
    )


def get_tenant_settings(session: Session, tenant_id: uuid.UUID) -> TenantSettings:
    """Return a tenant's settings, creating a default row on first access.

    Defaults: reporting currency ``USD``, timezone ``UTC``, empty FX table.
    """
    settings = session.scalar(tenant_scoped_select(TenantSettings, tenant_id))
    if settings is None:
        settings = TenantSettings(tenant_id=tenant_id)
        session.add(settings)
        session.flush()
    return settings


def update_tenant_settings(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    reporting_currency: str | None = None,
    reporting_timezone: str | None = None,
    fx_rates: dict[str, float] | None = None,
) -> TenantSettings:
    """Update a tenant's reporting settings (only the fields provided)."""
    settings = get_tenant_settings(session, tenant_id)
    if reporting_currency is not None:
        settings.reporting_currency = reporting_currency.strip().upper()
    if reporting_timezone is not None:
        settings.reporting_timezone = reporting_timezone.strip()
    if fx_rates is not None:
        # Normalize keys to upper-case ISO codes; drop non-positive rates.
        settings.fx_rates = {
            str(k).strip().upper(): float(v)
            for k, v in fx_rates.items()
            if float(v) > 0
        }
    session.flush()
    return settings
