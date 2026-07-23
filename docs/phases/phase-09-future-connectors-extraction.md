# Phase 9 — Partner Data Connectors & Extraction

**Depends on:** the full core (Phases 0–8) + enterprise-readiness phases, and the
source seam already realised in Phase 1 · **Status:** Done (connectors) — full
framework with mock partner clients, built across 09.1–09.8; **PDF/email
extraction sub-track remains Deferred**.

> **Built: full framework, mock partner clients.** The connector framework, SFTP
> source, partner adapters (Meta/Google Ads/DV360/TikTok), template-driven
> normalisation, credential storage, scheduling, and observability/admin are all
> implemented and tested against **fake/fixture partner clients** — live partner
> API calls sit behind a `ReportClient` seam enabled by injecting a real client
> plus stored credentials. **Exception:** the **PDF/email extraction** sub-track
> (below) remains **Deferred** — do not build it until explicitly scoped.

Cross-cutting: source-agnostic pipeline (CC-9), credential security (CC-10),
idempotent jobs (CC-6), traceability (CC-3), observability (CC-7).

## Objective

Extend ingestion beyond direct uploads to **all inbound partner sources**, all
feeding the **same** mapping → transform → validation → output pipeline via the
common `LandedDataset` (CC-9, ADR-010):

- **File sources:** SFTP drops (offline/retail sales, revenue, CRM, TV/radio/OOH,
  manual exports).
- **API sources (partner connectors):** call ad-platform reporting APIs — **Meta
  (Facebook/Instagram), Google Ads, DV360, TikTok** — to pull **each customer's
  own aggregate paid-media performance** (spend, impressions, clicks, conversions,
  reach — by date/campaign/geo/placement) from their authorised ad accounts.
  Customer-specific, **aggregate metrics only — no user-level PII.**

## Scope

- **In (future):** the `SourceConnector` framework for API sources; per-partner
  OAuth/credential management; SFTP file source; Meta as the reference connector;
  Google Ads / DV360 / TikTok against the same contract; scheduling + rolling
  incremental + backfill; per-partner default mapping/taxonomy templates; connector
  observability + admin.
- **Out / separate deferred track:** **PDF/email extraction** (unstructured →
  tabular via OCR/LLM). Kept isolated from the tabular pipeline; see the deferred
  sub-section below. Do not let its complexity leak into the core.

## Functional Requirements

- **P9-1 Source-agnostic (CC-9):** every connector implements the `SourceConnector`
  contract and emits a `LandedDataset`; nothing downstream branches on source.
- **P9-2 Credentials (CC-10):** OAuth2 per customer per partner (plus long-lived/
  system-user tokens where applicable); encrypted at rest, tenant-scoped,
  least-privilege read-only reporting scopes, auto-refresh, graceful expiry/
  revocation, **never logged**.
- **P9-3 Per-customer config:** account IDs, entities/metrics/dimensions, currency,
  timezone, incremental lookback window, backfill range, schedule.
- **P9-4 Scheduling & idempotency (CC-6):** scheduled async syncs; rolling-window
  incremental pulls to absorb partner restatements; backfill for history; per-
  partner rate limiting, pagination, retry/backoff; **re-pull replaces, never
  duplicates.**
- **P9-5 Default templates:** each connector ships default column→canonical
  mappings + taxonomy defaults (reusing the Phase-2 template layer), still
  human-ratifiable (CC-5).
- **P9-6 Observability (CC-7) & traceability (CC-3):** `sync_run` records status,
  window, row counts, errors, timing; landed data + output rows trace to
  `source`/`sync_run`.

## Deliverables

- `SourceConnector` framework for API sources + credential store (built on the
  seam already in `src/mmm_os/sources/`).
- SFTP source; Meta reference connector; Google Ads / DV360 / TikTok connectors.
- Scheduling/incremental/backfill orchestration (on Phase-7 Celery+Redis).
- Per-partner mapping/taxonomy template packs.
- Connector admin + observability surfaces.
- ORM + migrations for `source`, `connector`, `connector_config`,
  `connector_credential`, `sync_run` (documented in `data-model.md` Appendix C.1).

## Acceptance Criteria

- A connector configured for a test ad account pulls a date window into a
  `LandedDataset` that flows through the existing pipeline to `output_row`,
  traceable to its `sync_run`.
- Re-running the same window produces no duplicate output (CC-6).
- Credentials are stored encrypted and never appear in logs (CC-10).
- Partner data auto-maps via default templates with minimal human review, still
  gated by human ratification (CC-5).

## Dependencies

The full core (Phases 0–8). The source seam (`SourceConnector` / `LandedDataset` /
`FileSource`) already exists from Phase 1 (sub-phase [09.1](./phase-09.1-source-abstraction-landed-dataset.md)
documents it as foundational). Async scheduling depends on Phase 7 (Celery+Redis,
ADR-007); credential encryption depends on Phase 8.

## Open Questions

See `OQ-9.1…OQ-9.8` in [`../open-questions.md`](../open-questions.md): partner
priority, per-platform API approval lead times, auth model per partner, incremental
lookback + backfill depth, per-partner rate limits, aggregate-only confirmation,
currency/timezone source of truth, and SFTP layout/naming/PGP.

## Sub-phases

Designed as PR-sized sub-phases (one per branch/PR when built). 09.1 is
**foundational** and is already realised in code as the Phase-1 source seam.

- [`phase-09.1-source-abstraction-landed-dataset.md`](./phase-09.1-source-abstraction-landed-dataset.md) — source-agnostic abstraction + common landed representation.
- [`phase-09.2-connector-framework-credentials.md`](./phase-09.2-connector-framework-credentials.md) — connector contract + OAuth/credential management.
- [`phase-09.3-sftp-source.md`](./phase-09.3-sftp-source.md) — SFTP file source (per-tenant dirs, naming, optional PGP).
- [`phase-09.4-partner-connector-meta.md`](./phase-09.4-partner-connector-meta.md) — Meta reference connector (first end-to-end partner).
- [`phase-09.5-partner-connectors-google-dv360-tiktok.md`](./phase-09.5-partner-connectors-google-dv360-tiktok.md) — remaining partners on the same contract.
- [`phase-09.6-scheduling-incremental-backfill.md`](./phase-09.6-scheduling-incremental-backfill.md) — scheduling, rolling incremental, backfill, rate limits/retries.
- [`phase-09.7-partner-mapping-taxonomy-templates.md`](./phase-09.7-partner-mapping-taxonomy-templates.md) — default mapping/taxonomy templates per partner.
- [`phase-09.8-connector-observability-admin.md`](./phase-09.8-connector-observability-admin.md) — sync status, last-successful-pull, row counts, admin hooks.

---

## Deferred sub-track — PDF/email extraction (unstructured → tabular)

**Preserved from the original Phase 9 scope; deferred independently of the
connector work above and lower priority.** Keep isolated from the core tabular
pipeline.

- **9x-1** An OCR/LLM extraction step that turns unstructured PDF/email input into
  candidate tables *before* the normal pipeline (which then treats them as a
  landed dataset).
- **9x-2** A **mandatory human-review fallback** for low-confidence extractions
  (highest failure rate of any source; never auto-trust).
- **Open:** whether/when to add PDF/email extraction (PRD §2.3); per-source
  maintenance budget; isolation boundary so extraction failures never destabilise
  the tabular core.
