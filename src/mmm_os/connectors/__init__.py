"""Partner data connectors (Phase 9 — full framework, mock partner clients).

Each connector is a :class:`~mmm_os.sources.base.SourceConnector` implementation
for a specific inbound partner: file-based (``sftp``) or API-based (``meta``,
``google_ads``, ``dv360``, ``tiktok``). They emit the common
:class:`~mmm_os.sources.landed.LandedDataset`, so downstream phases are unaffected
by which partner produced the data (CC-9).

The framework is real and tested; **live partner API calls sit behind a
``ReportClient`` seam** (:mod:`mmm_os.connectors.base`) that is satisfied by a
fake fixture client in dev/tests and by a real client + stored credentials in
production. Credentials go through the ``SecretStore`` (CC-10/CC-12). The
PDF/email extraction sub-track remains deferred. See
``docs/phases/phase-09-future-connectors-extraction.md`` and ADR-010 in
``docs/architecture.md``.
"""

from mmm_os.connectors.registry import (
    CONNECTOR_KEYS,
    PARTNER_KEYS,
    build_partner_connector,
)

__all__ = ["CONNECTOR_KEYS", "PARTNER_KEYS", "build_partner_connector"]
