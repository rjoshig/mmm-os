"""Partner data connectors (Phase 9 — deferred; placeholders only).

Each connector is a :class:`~mmm_os.sources.base.SourceConnector` implementation
for a specific inbound partner: file-based (``sftp``) or API-based (``meta``,
``google_ads``, ``dv360``, ``tiktok``). They emit the common
:class:`~mmm_os.sources.landed.LandedDataset`, so downstream phases are unaffected
by which partner produced the data (CC-9).

**No implementation lives here yet.** These modules are structural placeholders
that fix the package layout and responsibilities so the Phase-9 build attaches
without a refactor. See ``docs/phases/phase-09-future-connectors-extraction.md``
and ADR-010 in ``docs/architecture.md``.
"""
