# Phase 9.5 — Partner Connectors: Google Ads, DV360, TikTok

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.4 · **Status:** Deferred (designed).

## Objective

Implement the remaining priority partners — **Google Ads, DV360, TikTok** —
against the **same** `SourceConnector` contract established by Meta (09.4).

## Scope

- **In:** per-partner auth + aggregate paid-media pulls + normalisation into
  `LandedDataset`; per-partner default mapping/taxonomy templates (with 09.7).
- **Out:** partners beyond these three (future); scheduling internals (09.6).

## Functional Requirements

- **P9.5-1** Each partner reuses the 09.2 framework + 09.4 reference pattern; only
  partner-specific auth, endpoints, and field maps differ.
- **P9.5-2** Aggregate metrics only, per authorised account (OQ-9.6).
- **P9.5-3** Normalise into a `LandedDataset`; record a `sync_run`; trace landed
  data to it (CC-3, CC-7).
- **P9.5-4** Idempotent re-pulls (CC-6).

## Deliverables

- `src/mmm_os/connectors/google_ads/`, `dv360/`, `tiktok/` implementations
  (currently placeholders).
- Per-partner default mapping/taxonomy templates.

## Acceptance Criteria

- Each connector pulls a test account's window into a `LandedDataset` that flows
  through the pipeline to `output_row`, traceable to its `sync_run`.
- Adding a partner requires no downstream pipeline changes (CC-9).

## Dependencies

09.4 (reference), 09.2 (framework/credentials), 09.7 (templates).

## Open Questions

OQ-9.1 (partner order), OQ-9.2 (Google Ads developer token / TikTok API access),
OQ-9.5 (per-partner rate limits), OQ-9.7 (currency/timezone).

## Sub-phases

N/A (leaf sub-phase).
