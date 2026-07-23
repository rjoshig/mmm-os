# Phase 9.6 — Scheduling, Incremental & Backfill

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.2, Phase 7 (Celery+Redis) · **Status:** Done — full framework with mock partner clients (live API calls behind a `ReportClient` seam).

## Objective

Run connector syncs on a schedule with **rolling-window incremental** pulls,
**backfill** for history, and robust rate-limit/retry handling — all idempotent
(CC-6).

## Scope

- **In:** scheduled async syncs (on the Phase-7 queue, ADR-007); rolling lookback
  window; backfill range; per-partner rate limiting, pagination, retry/backoff;
  idempotent replace-not-duplicate semantics.
- **Out:** partner-specific pull logic (09.4/09.5).

## Functional Requirements

- **P9.6-1** Per-`connector_config` schedule drives async syncs via workers.
- **P9.6-2** **Rolling lookback window** re-pulls recent dates to absorb
  partner-side restatements; **re-pull replaces, never duplicates** (CC-6).
- **P9.6-3** **Backfill** pulls a bounded historical range on demand.
- **P9.6-4** Per-partner **rate limiting, pagination, retry/backoff**; failures
  are recorded on the `sync_run` (CC-7), not crashes.

## Deliverables

- `src/mmm_os/connectors/scheduling.py` implementation (currently a placeholder).
- `sync_run` lifecycle + idempotent upsert of a window's output.
- **In-app scheduler (Cycle 3, Slice 3):** `connectors/autoschedule.py` — a config's
  `settings.schedule.interval_minutes` drives `run_due_syncs(session, now)` (pure,
  tested). A background loop (`SCHEDULER_ENABLED`, off by default) and a manual
  `POST /scheduler/run-due` both call it; `PUT …/schedule` sets/clears the interval.
  UI: per-source schedule selector + "Run due now" on the Sources screen.

## Acceptance Criteria

- A scheduled sync pulls only the incremental window; a restated metric within the
  lookback is corrected without duplicate rows.
- A backfill request loads history within the configured range.
- Rate-limit/transient errors retry with backoff and are recorded.

## Dependencies

09.2 (framework), Phase 7 (Celery+Redis), 09.4/09.5 (partners to schedule).

## Open Questions

OQ-9.4 (lookback + backfill depth), OQ-9.5 (rate limits).

## Sub-phases

N/A (leaf sub-phase).
