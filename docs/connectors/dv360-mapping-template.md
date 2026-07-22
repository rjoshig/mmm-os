# DV360 (Display & Video 360) — Default Mapping Template

Maps DV360 Bid Manager API offline-report fields onto the
[canonical schema](../canonical-schema.md) and **auto-applies on every DV360
connector pull**, so standard data lands as canonical rows with **zero manual
mapping** for the common case. It is config-as-data (CC-4); the machine-readable
source is
[`src/mmm_os/connectors/dv360/templates/default_mapping.yaml`](../../src/mmm_os/connectors/dv360/templates/default_mapping.yaml).
It sits at the **`template` layer** of the Phase-2 layered config, so a tenant may
**override any field per tenant** (customer overrides win). It follows the
[Meta reference pattern](./meta-mapping-template.md) and completes the four
priority partners (Meta, Google Ads, TikTok, DV360).

> **Provisional field names.** The exact Bid Manager filter/metric names, cost
> metric, and hierarchy levels below are **provisional** and MUST be confirmed
> against the live DV360 / Bid Manager API version when Phase 09.5 is implemented
> (OQ-9.x).

## Mapping table

| Canonical field | DV360 source | Notes |
|---|---|---|
| `date` | `FILTER_DATE` | `parse_date` → ISO date. |
| `channel` | *(constant)* `"Programmatic"` | DV360 is a programmatic DSP; modeling decision (see notes). |
| `sub_channel` | *(none)* | Optionally `FILTER_EXCHANGE` / format; off by default. |
| `campaign` | `FILTER_MEDIA_PLAN` | DV360 "Campaign" / Media Plan. |
| `ad_group` | `FILTER_INSERTION_ORDER` | Insertion Order ≈ canonical `ad_group`. |
| `geo` | `FILTER_COUNTRY` | `map_value` via canonical `geo` (ISO-like). |
| `product` | *(none)* | Not from DV360 reporting. |
| `funnel_stage` | *(none)* | Not reliably derivable; optional. |
| `spend` | `METRIC_REVENUE_ADVERTISER` | Advertiser-currency cost; **which cost metric = spend is per-tenant** (see notes). |
| `impressions` | `METRIC_IMPRESSIONS` | Direct. |
| `clicks` | `METRIC_CLICKS` | Direct. |
| `conversions` | `METRIC_TOTAL_CONVERSIONS` | Depends on the advertiser's conversion setup. |
| `revenue` | *(none)* | Media reports carry cost, not sales revenue; set per tenant. |
| `reach` | *(none)* | Not in the standard offline report. |
| `currency` | *(account)* | Advertiser currency, from account settings — not a per-row column. |

## Key nuances

1. **Async offline CSV report.** DV360 reporting is a Bid Manager **query** you
   create, run, poll, and then **download as a CSV** from a signed URL. It is
   API-based but delivered as a **file**, so it lands like a flat table (one header
   row) rather than a JSON row set.
2. **Trailing grand-total / summary rows.** The Bid Manager CSV appends
   grand-total (and sometimes blank/metadata) rows after the data. These must be
   **stripped before mapping** (`strip_report_totals` op) or they pollute totals.
3. **Multiple cost metrics.** DV360 exposes several —
   `METRIC_REVENUE_ADVERTISER`, `METRIC_MEDIA_COST_ADVERTISER`,
   `METRIC_TOTAL_MEDIA_COST_ADVERTISER`, `METRIC_BILLABLE_COST_ADVERTISER`. **Which
   one counts as "spend" depends on the billing/markup model** and is a per-tenant
   decision. The template defaults to `METRIC_REVENUE_ADVERTISER` (what the
   advertiser pays); override as needed.
4. **Hierarchy naming.** DV360's hierarchy is **Media Plan (campaign) → Insertion
   Order (≈ ad_group) → Line Item**. The default maps campaign←Media Plan and
   ad_group←Insertion Order; when pulling deeper (line-item) levels, adjust the
   group-bys and mapping accordingly.
5. **`channel` = `"Programmatic"` (modeling decision).** DV360 buys programmatic
   display/video across exchanges. We fix `channel = "Programmatic"`; the
   **alternative** is a platform label (`"DV360"` / `"Google"`) if a tenant models
   DV360 as its own channel — overridable per tenant, and part of the cross-partner
   channel-naming question.
6. **Currency isn't a per-row column.** Cost is in the **advertiser's currency**,
   fetched from account settings (`__account__` sentinel), not a report column.
7. **Revenue vs cost.** DV360 media reports carry **cost**, not sales revenue;
   `revenue` is left null and set per tenant if a conversion-value metric applies.
8. **No native reach** in the standard offline report (like Google Ads).

## Reference pattern

Follows the [Meta reference pattern](./meta-mapping-template.md): `connector` +
`schema_version`, a `report` spec, a `column_map` (with ops like `parse_date` /
`map_value` / `__constant__` / `strip_report_totals`), and partner `taxonomies`
that resolve into the canonical taxonomies (empty here — `geo` uses the canonical
taxonomy directly). See
[phase-09.7](../phases/phase-09.7-partner-mapping-taxonomy-templates.md) for the
per-partner template contract and
[phase-09.5](../phases/phase-09.5-partner-connectors-google-dv360-tiktok.md) for
the connector build.
