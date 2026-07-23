# Canonical Schema & Standard Taxonomies

**Status:** Draft v0.1 (Appendix A + Appendix B of the Build Plan).
**Role:** the **fixed target contract**. Mapping (Phase 2), transformation rules
(Phase 3), and AI suggestions (Phase 5) all resolve *to* these fields and
vocabularies. Per Phase 0 (P0-1/P0-2), the canonical schema and taxonomies MUST
be defined as **machine-readable config** (e.g. versioned `canonical_schema.yaml`
+ `taxonomies.yaml`) that the app loads and validates at startup — never
hardcoded.

MMM data is stored **long/tidy**: one row per (date × dimensions × measure-set).
The field list below is a starting point — refine in Phase 0.

---

## Appendix A — Canonical Schema (draft v0.1)

### A.1 Dimension fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `date` | date | **Yes** | Period date; normalized to ISO. Granularity per A.4. |
| `channel` | enum(taxonomy) | **Yes** | Top-level channel (see Appendix B). |
| `sub_channel` | enum(taxonomy) | No | Platform/placement under channel. |
| `campaign` | string | No | Campaign name (raw kept + standardized). |
| `ad_group` | string | No | Ad set / line item. |
| `geo` | enum(taxonomy) | No | Market/region/country. |
| `product` | string | No | Product / brand / SKU. |
| `funnel_stage` | enum(taxonomy) | No | e.g. awareness/consideration/conversion. |

### A.2 Measure fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `spend` | number | No\* | In `currency`; normalized. |
| `impressions` | number | No | |
| `clicks` | number | No | |
| `conversions` | number | No | |
| `revenue` | number | No | |
| `reach` | number | No | |

\* At least one measure **or one factor** (see A.2b) MUST be present for a row to be
meaningful. **OQ-2.2 resolved (see A.4):** the required set for v1 is `date` +
`channel` + **≥1 measure or factor**; all other fields are optional.

### A.2b Factor fields (MMM external regressors) — Cycle 2

Non-media drivers a marketing-mix model controls for. A **factor source** (e.g. a
weekly price index, holiday calendar, or weather series) carries `date` + one or
more of these instead of media measures, so a factor satisfies the "meaningful row"
requirement in place of a measure. Factors are a **distinct group** from dimensions
and measures and are mappable targets in the mapping UI (`kind: "factor"`).

| Field | Type | Category | Notes |
|---|---|---|---|
| `seasonality_index` | number | Seasonality | Index; baseline ~1.0 or 100. |
| `is_holiday` | boolean | Holidays | Period contains a holiday. |
| `holiday_name` | string | Holidays | Holiday label (raw kept + standardized). |
| `price_index` | number | Price | Price factor relative to a baseline. |
| `on_promotion` | boolean | Promotions | Promotion active in the period. |
| `promotion_depth` | number | Promotions | Discount depth (fraction / %). |
| `distribution` | number | Distribution | Weighted distribution or % ACV. |
| `avg_temperature` | number | Weather | Average temperature for the period. |
| `precipitation` | number | Weather | Precipitation for the period. |
| `macro_index` | number | Macro | Consumer confidence / CPI proxy. |
| `competitor_spend` | number | Competitor | Estimated competitor activity. |

### A.3 Metadata fields (system-populated)

| Field | Type | Notes |
|---|---|---|
| `tenant_id` | id | Always present (CC-1). |
| `currency` | enum | ISO currency; drives `convert_currency`. |
| `source_file_id` | id | Traceability (CC-3). |
| `source_sheet` | string | Traceability. |
| `source_row` | int | Traceability. |
| `mapping_config_version` | int | Traceability. |
| `rule_set_version` | int | Traceability. |
| `ingested_at` | timestamp | |

### A.4 Schema decisions

**Resolved:**
- **Required fields (OQ-2.2):** `date` + `channel` (dimensions) and **≥1 measure or
  factor** per row. All other dimension, measure, and factor fields are optional. A
  row missing a required field blocks output (see Phase 2 P2-5 / Phase 4 severity
  policy).
- **Factors (Cycle 2):** MMM external regressors are a first-class field group
  (A.2b), mappable and validated; a factor source needs no media measure.
- **Date granularity (Cycle 2):** `date` is stored at its native grain; the
  supported **modelling grains are daily → weekly → monthly**, with **weekly the
  MMM-standard target**. Reconciliation is explicit, not implicit: the declarative
  **`aggregate`** transform op rolls a finer grain up to a coarser one — measures
  summed, numeric factors averaged, dimensions preserved as grouping keys, and the
  series made **continuous** (gap-filled) so it is adstock-ready. Mixed-grain sources
  are reconciled by aggregating each to the tenant's chosen target grain; the
  platform does **not** silently up-sample coarser data to a finer grain.

**Still open:**
- Whether measures are columns (wide) or a `metric`/`value` pair (long-long). Draft assumes measure-columns.

---

## Appendix B — Standard Taxonomies (draft)

Controlled vocabularies that `map_value` rules resolve raw values into. These are
**seed lists — extend in Phase 0** and store as machine-readable config.

- **channel:** `Facebook`, `Google`, `TikTok`, `YouTube`, `Programmatic`, `TV`, `Radio`, `OOH`, `Print`, `Email`, `Affiliate`, `Other`.
- **funnel_stage:** `Awareness`, `Consideration`, `Conversion`, `Retention`.
- **geo:** ISO country/region set (define scope in Phase 0).
- **currency:** ISO 4217 codes.

Each taxonomy MUST support **synonyms/aliases** (e.g. `FB`, `fb_ads`,
`facebook ads` → `Facebook`). Aliases are stored in the data model as
`taxonomy_alias` records (see [`data-model.md`](./data-model.md)).

**Partner-supplied source taxonomies.** Partner connectors (Phase 9) ship their
own **source-value taxonomies** that resolve **into** these canonical taxonomies —
e.g. Meta's `meta_publisher_platform` (`instagram` → canonical `sub_channel`
`Instagram`) and `meta_objective_to_funnel` (`OUTCOME_SALES` → canonical
`funnel_stage` `Conversion`). These live **alongside their connector** (e.g.
`src/mmm_os/connectors/meta/templates/default_mapping.yaml`), not here; the
**canonical taxonomies above remain the single target** everything resolves to.
See [`connectors/meta-mapping-template.md`](./connectors/meta-mapping-template.md)
for the worked Meta example and [`phases/phase-09.7-partner-mapping-taxonomy-templates.md`](./phases/phase-09.7-partner-mapping-taxonomy-templates.md)
for the per-partner contract.

---

_Living document — the authoritative machine-readable spec (`canonical_schema.yaml`
/ `taxonomies.yaml`) is produced in Phase 0; this doc mirrors and explains it._
