"""I/O profile resolution + update (Phase 14, CC-14).

Resolves the logical storage roots for a tenant by layering:
per-tenant ``io_profile`` row → global-default ``io_profile`` row → env defaults
(``Settings``). Every root always resolves to a non-empty prefix, so the
file/output lifecycle never has an undefined destination.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from mmm_os.core.config import Settings, get_settings
from mmm_os.models import IoProfile

_ROOTS = ("input", "output", "temp", "archive", "error", "reject")


@dataclass(frozen=True)
class ResolvedIoProfile:
    """The fully-resolved logical roots (storage key prefixes) for a tenant."""

    input: str
    output: str
    temp: str
    archive: str
    error: str
    reject: str

    def prefix(self, root: str) -> str:
        """Return the resolved prefix for a logical root name (``output`` etc.)."""
        mapping: dict[str, str] = {
            "input": self.input,
            "output": self.output,
            "temp": self.temp,
            "archive": self.archive,
            "error": self.error,
            "reject": self.reject,
        }
        if root not in mapping:
            raise ValueError(f"unknown io root {root!r}")
        return mapping[root]


def _env_defaults(settings: Settings) -> dict[str, str]:
    return {
        "input": settings.io_input_prefix,
        "output": settings.io_output_prefix,
        "temp": settings.io_temp_prefix,
        "archive": settings.io_archive_prefix,
        "error": settings.io_error_prefix,
        "reject": settings.io_reject_prefix,
    }


def _row_values(profile: IoProfile | None) -> dict[str, str | None]:
    if profile is None:
        return {root: None for root in _ROOTS}
    return {
        "input": profile.input_path,
        "output": profile.output_path,
        "temp": profile.temp_path,
        "archive": profile.archive_path,
        "error": profile.error_path,
        "reject": profile.reject_path,
    }


def get_global_default(session: Session) -> IoProfile | None:
    """Return the global-default profile (``tenant_id IS NULL``), if one exists."""
    return session.scalar(select(IoProfile).where(IoProfile.tenant_id.is_(None)))


def get_tenant_profile(session: Session, tenant_id: uuid.UUID) -> IoProfile | None:
    """Return a tenant's own profile row, if one exists."""
    return session.scalar(select(IoProfile).where(IoProfile.tenant_id == tenant_id))


def resolve_io_profile(
    session: Session, tenant_id: uuid.UUID, settings: Settings | None = None
) -> ResolvedIoProfile:
    """Resolve the effective roots: tenant → global default → env defaults."""
    settings = settings or get_settings()
    defaults = _env_defaults(settings)
    global_row = _row_values(get_global_default(session))
    tenant_row = _row_values(get_tenant_profile(session, tenant_id))
    resolved = {
        root: (tenant_row[root] or global_row[root] or defaults[root]) for root in _ROOTS
    }
    return ResolvedIoProfile(**resolved)


def update_io_profile(
    session: Session,
    tenant_id: uuid.UUID | None,
    *,
    input_path: str | None = None,
    output_path: str | None = None,
    temp_path: str | None = None,
    archive_path: str | None = None,
    error_path: str | None = None,
    reject_path: str | None = None,
) -> IoProfile:
    """Create/update a tenant's (or the global-default's) I/O profile row.

    Pass ``tenant_id=None`` to write the global default. Only the roots provided
    are set; passing an empty string clears a root back to the fallback chain.
    """
    profile = (
        get_global_default(session)
        if tenant_id is None
        else get_tenant_profile(session, tenant_id)
    )
    if profile is None:
        profile = IoProfile(tenant_id=tenant_id)
        session.add(profile)

    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().strip("/")
        return value or None

    if input_path is not None:
        profile.input_path = _clean(input_path)
    if output_path is not None:
        profile.output_path = _clean(output_path)
    if temp_path is not None:
        profile.temp_path = _clean(temp_path)
    if archive_path is not None:
        profile.archive_path = _clean(archive_path)
    if error_path is not None:
        profile.error_path = _clean(error_path)
    if reject_path is not None:
        profile.reject_path = _clean(reject_path)
    session.flush()
    return profile
