"""Pydantic v2 schemas for per-tenant reporting settings (Cycle 2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TenantSettingsRead(BaseModel):
    """A tenant's reporting settings as returned to the UI."""

    model_config = ConfigDict(from_attributes=True)

    reporting_currency: str
    reporting_timezone: str
    fx_rates: dict[str, float]


class TenantSettingsUpdate(BaseModel):
    """A partial update to a tenant's reporting settings (only provided fields)."""

    reporting_currency: str | None = Field(default=None, min_length=3, max_length=3)
    reporting_timezone: str | None = Field(default=None, min_length=1, max_length=64)
    fx_rates: dict[str, float] | None = None
