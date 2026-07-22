"""Connector sync orchestration (Phase 9 — deferred; placeholder only).

Will define the scheduled-sync interface: async workers (riding the Phase-7
Celery+Redis queue, ADR-007) run per-connector syncs; incremental pulls use a
rolling lookback window to absorb partner-side restatements; backfill covers
history; re-pulling a window **replaces, never duplicates** (idempotent, CC-6).
Each run is recorded as a ``sync_run`` (status, window, row counts, errors).

No logic is implemented yet — see Phase 9.6.
"""
