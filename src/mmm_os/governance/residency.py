"""Data-residency enforcement (Phase 10, P10-4).

A customer declares a home **region** (Slice 7.1). Residency means its data stays
in that region — in particular, an enterprise customer's dedicated (silo) database
must live on region-appropriate infrastructure. This module enforces that at the
application layer when a silo is provisioned: the dedicated DB URL's host must be
allowed for the customer's region.

Enforcement is config-driven and **off by default** (single-region v1). Set
``RESIDENCY_ENFORCED=true`` and provide a region→allowed-host-substrings map via
``RESIDENCY_REGION_HOSTS`` (e.g. ``eu=eu-,europe;us=us-,useast``) to turn it on. The
network/infra layer (Phase 11) is the primary control; this is defense in depth so a
misrouted silo URL is rejected before any data lands.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from mmm_os.core.config import Settings


class ResidencyError(ValueError):
    """Raised when a resource would violate a customer's data-residency region."""


def _region_host_map(settings: Settings) -> dict[str, list[str]]:
    """Parse ``RESIDENCY_REGION_HOSTS`` into ``{region: [host substrings]}``."""
    mapping: dict[str, list[str]] = {}
    raw = settings.residency_region_hosts.strip()
    if not raw:
        return mapping
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry or "=" not in entry:
            continue
        region, hosts = entry.split("=", 1)
        substrings = [h.strip().lower() for h in hosts.split(",") if h.strip()]
        if substrings:
            mapping[region.strip().lower()] = substrings
    return mapping


def _host_of(url: str) -> str:
    """Return the lowercased host of a SQLAlchemy URL (best-effort)."""
    # SQLAlchemy URLs look like scheme://user@host:port/db; urlsplit handles it once
    # the leading "dialect+driver" scheme is normalised to a single token.
    normalized = url.replace("+", "-", 1)
    return (urlsplit(normalized).hostname or "").lower()


def check_database_residency(settings: Settings, region: str, database_url: str) -> None:
    """Validate a dedicated DB URL is allowed for ``region``.

    No-op unless ``RESIDENCY_ENFORCED`` is set. When enforced, the URL's host must
    contain one of the region's allowed substrings; a region with no configured
    hosts, or a host that matches none, is rejected.

    Raises:
        ResidencyError: If enforcement is on and the URL host is not allowed here.
    """
    if not settings.residency_enforced:
        return
    allowed = _region_host_map(settings).get(region.lower())
    if not allowed:
        raise ResidencyError(
            f"no residency hosts configured for region {region!r}; refusing to place data"
        )
    host = _host_of(database_url)
    if not any(sub in host for sub in allowed):
        raise ResidencyError(
            f"database host {host!r} is not allowed for region {region!r} (residency)"
        )
