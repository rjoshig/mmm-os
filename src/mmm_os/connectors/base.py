"""Partner connector base (Phase 9 — deferred; placeholder only).

Will provide the shared scaffolding for API-based partner connectors on top of
:class:`~mmm_os.sources.base.SourceConnector`: pagination, rate limiting,
retry/backoff, and normalisation of a partner report response into a
:class:`~mmm_os.sources.landed.LandedDataset` (records + known column schema).
Concrete partners (``meta``, ``google_ads``, ``dv360``, ``tiktok``) subclass it.

No logic is implemented yet — see Phase 9.2.
"""
