"""Connector catalog: the in-code registry of known connectors (Phase 9).

The ``connector`` catalog is code, not a table — connectors are implementations.
This maps a connector key to its :class:`PartnerConnector` class + a fake report
client used for dev/tests (real clients are injected with credentials).
"""

from __future__ import annotations

from typing import Any

from mmm_os.connectors.base import PartnerConnector, ReportClient
from mmm_os.connectors.dv360.connector import Dv360Connector, FakeDv360ReportClient
from mmm_os.connectors.google_ads.connector import (
    FakeGoogleAdsReportClient,
    GoogleAdsConnector,
)
from mmm_os.connectors.meta.connector import FakeMetaReportClient, MetaConnector
from mmm_os.connectors.tiktok.connector import FakeTikTokReportClient, TikTokConnector

_PARTNERS: dict[str, tuple[type[PartnerConnector], type[ReportClient]]] = {
    "meta": (MetaConnector, FakeMetaReportClient),
    "google_ads": (GoogleAdsConnector, FakeGoogleAdsReportClient),
    "dv360": (Dv360Connector, FakeDv360ReportClient),
    "tiktok": (TikTokConnector, FakeTikTokReportClient),
}

#: API-based partner connectors.
PARTNER_KEYS = frozenset(_PARTNERS)
#: All known connector keys (partners + the SFTP file source).
CONNECTOR_KEYS = PARTNER_KEYS | {"sftp"}


def build_partner_connector(
    key: str,
    *,
    account_ctx: dict[str, Any] | None = None,
    client: ReportClient | None = None,
) -> PartnerConnector:
    """Build a partner connector, defaulting to its fake client (dev/tests)."""
    if key not in _PARTNERS:
        raise KeyError(f"unknown partner connector: {key!r}")
    connector_cls, fake_cls = _PARTNERS[key]
    return connector_cls(client or fake_cls(), account_ctx=account_ctx)
