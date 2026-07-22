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

**Worked examples (default templates, conforming to the Phase-09.7 contract):**
- Google Ads — [`docs/connectors/google-ads-mapping-template.md`](../connectors/google-ads-mapping-template.md)
  + [`default_mapping.yaml`](../../src/mmm_os/connectors/google_ads/templates/default_mapping.yaml).
- TikTok — [`docs/connectors/tiktok-mapping-template.md`](../connectors/tiktok-mapping-template.md)
  + [`default_mapping.yaml`](../../src/mmm_os/connectors/tiktok/templates/default_mapping.yaml).
- DV360 — [`docs/connectors/dv360-mapping-template.md`](../connectors/dv360-mapping-template.md)
  + [`default_mapping.yaml`](../../src/mmm_os/connectors/dv360/templates/default_mapping.yaml).

## Functional Requirements

- **P9.5-1** Each partner reuses the 09.2 framework + 09.4 reference pattern; only
  partner-specific auth, endpoints, and field maps differ.
- **P9.5-2** Aggregate metrics only, per authorised account (OQ-9.6).
- **P9.5-3** Normalise into a `LandedDataset`; record a `sync_run`; trace landed
  data to it (CC-3, CC-7).
- **P9.5-4** Idempotent re-pulls (CC-6).
- **P9.5-5 New transform ops.** These connectors need partner-specific operations
  the Phase-3 library must support (new handlers, no rewrite — P3-2), tracked on
  [phase-03](./phase-03-transformation-rule-engine.md):
  - **Google Ads:** `micros_to_currency` (÷ 1,000,000 on `cost_micros`),
    `resolve_geo_target` (geo-target-constant ID → country).
  - **TikTok:** `flatten_report_row` (merge the split `dimensions`/`metrics`
    objects), and string→number `cast_type` (numeric metrics arrive as strings).
  - **DV360:** `strip_report_totals` (drop the trailing grand-total/summary rows
    of the Bid Manager CSV before mapping).
  - *(Meta already contributed `extract_action`.)*

## Deliverables

- `src/mmm_os/connectors/google_ads/`, `dv360/`, `tiktok/` implementations
  (currently placeholders).
- Per-partner default mapping/taxonomy templates.

## Acceptance Criteria

- Each connector pulls a test account's window into a `LandedDataset` that flows
  through the pipeline to `output_row`, traceable to its `sync_run`.
- Adding a partner requires no downstream pipeline changes (CC-9).
- **Google Ads:** a campaign pull yields canonical rows with **spend correctly
  de-micro'd**, `channel`/`sub_channel` set, and conversions/revenue populated —
  zero manual mapping for the standard case.
- **TikTok:** a pull yields canonical rows with the **split response flattened**,
  string metrics **cast to number**, and `channel`/`geo` set — zero manual mapping
  for the standard case.
- **DV360:** a Bid Manager report pull yields canonical rows with the **trailing
  total rows stripped**, the chosen cost metric mapped to `spend`, and
  `channel`/`campaign`/`ad_group`/`geo` set — zero manual mapping for the standard
  case.

## Dependencies

09.4 (reference), 09.2 (framework/credentials), 09.7 (templates).

## Open Questions

OQ-9.1 (partner order), OQ-9.2 (Google Ads developer token / TikTok API access),
OQ-9.5 (per-partner rate limits), OQ-9.7 (currency/timezone).

## Sub-phases

N/A (leaf sub-phase).
