# Phase 9.4 — Partner Connector: Meta (Reference)

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.2 · **Status:** Deferred (designed).

## Objective

Implement **Meta (Facebook/Instagram)** end-to-end as the **reference** API
connector — the template every other partner follows against the same contract.

## Scope

- **In:** Meta reporting API auth + pull of aggregate paid-media performance
  (spend, impressions, clicks, conversions, reach — by date/campaign/geo/
  placement); normalisation into a `LandedDataset`; the first per-partner default
  mapping/taxonomy template (with 09.7).
- **Out:** other partners (09.5); scheduling (09.6).

## Functional Requirements

- **P9.4-1** Authenticate against a customer's authorised Meta ad accounts
  (OAuth2 / system-user token) via the 09.2 credential store.
- **P9.4-2** Pull **aggregate metrics only** for a requested date window — **no
  user-level PII** (OQ-9.6).
- **P9.4-3** Normalise the response into a `LandedDataset` with a known column
  schema (no header detection).
- **P9.4-4** Record a `sync_run` (window, row counts, status, errors) (CC-7); the
  landed data traces back to it (CC-3).

## Deliverables

- `src/mmm_os/connectors/meta/` implementation (currently a placeholder).
- Meta default mapping/taxonomy template (e.g. `spend` → `spend`, platform →
  `Facebook`).

## Acceptance Criteria

- A configured test Meta account pulls a date window into a `LandedDataset` that
  flows through mapping→transform→validation→output, traceable to its `sync_run`.
- Re-pulling the window replaces, never duplicates (CC-6).

## Dependencies

09.2 (framework + credentials); 09.7 (templates); 09.6 (scheduling, once added).

## Open Questions

OQ-9.2 (Meta app review lead time), OQ-9.3 (auth model), OQ-9.6 (aggregate-only).

## Sub-phases

N/A (leaf sub-phase).
