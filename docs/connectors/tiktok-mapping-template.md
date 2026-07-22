# TikTok — Default Mapping Template

Maps TikTok Marketing API (`/report/integrated/get/`) fields onto the
[canonical schema](../canonical-schema.md) and **auto-applies on every TikTok
connector pull**, so standard data lands as canonical rows with **zero manual
mapping** for the common case. It is config-as-data (CC-4); the machine-readable
source is
[`src/mmm_os/connectors/tiktok/templates/default_mapping.yaml`](../../src/mmm_os/connectors/tiktok/templates/default_mapping.yaml).
It sits at the **`template` layer** of the Phase-2 layered config, so a tenant may
**override any field per tenant** (customer overrides win). It follows the
[Meta reference pattern](./meta-mapping-template.md); see also the
[DV360 template](./dv360-mapping-template.md).

> **Provisional field names.** The exact metric/dimension names, conversion event,
> and value-metric name below are **provisional** and MUST be confirmed against the
> live TikTok Marketing API version when Phase 09.5 is implemented (OQ-9.x).

## Mapping table

| Canonical field | TikTok source | Notes |
|---|---|---|
| `date` | `dimensions.stat_time_day` | `parse_date` → ISO date. |
| `channel` | *(constant)* `"TikTok"` | Fixed per connector. |
| `sub_channel` | *(none)* | Not set by default. |
| `campaign` | `metrics.campaign_name` | Name requested **as a metric** (dimensions give IDs). |
| `ad_group` | *(none)* | Set `adgroup_name` when `data_level = AUCTION_ADGROUP`. |
| `geo` | `dimensions.country_code` | `map_value` via canonical `geo` (ISO-like code). |
| `product` | *(none)* | Not from TikTok reporting. |
| `funnel_stage` | *(none)* | Optional; could derive from `objective_type`. |
| `spend` | `metrics.spend` | `cast_type → number` (returned as string). Account currency. |
| `impressions` | `metrics.impressions` | `cast_type → number`. |
| `clicks` | `metrics.clicks` | `cast_type → number`. **All** clicks; prefer destination clicks (configurable). |
| `reach` | `metrics.reach` | `cast_type → number`. |
| `conversions` | `metrics.conversion` | `cast_type → number`. Event depends on optimization goal. |
| `revenue` | *(none — provisional)* | Value-metric name depends on the conversion event; set per tenant. |
| `currency` | *(account)* | **Not in the report row** — fetched from advertiser account info. |

## Key nuances

1. **Split response shape.** Each row returns `dimensions` and `metrics` as
   **separate nested objects** (`{dimensions:{…}, metrics:{…}}`). They must be
   **flattened into one row** (`flatten_report_row` op) before mapping.
2. **Numbers as strings.** All numeric metrics come back as **strings** and must be
   cast to number (`cast_type: number`) — hence the explicit op on every measure.
3. **IDs vs names.** Dimensions return **IDs** (e.g. `campaign_id`); human-readable
   names like `campaign_name` must be **explicitly requested in the metrics list**.
4. **Clicks (all) vs (destination).** `clicks` is **all** clicks; for real traffic
   prefer **destination/landing-page** clicks (configurable — parallels Meta's
   `inline_link_clicks`).
5. **Conversion & value depend on the optimization event/attribution.** The
   conversion **value** metric name is **provisional and set per tenant**, so
   `revenue` is left **null** in the default rather than guessed.
6. **Currency isn't in the report.** It is fetched from **advertiser account info**
   (`__account__` sentinel), not a report column.
7. **Sync vs async reports.** Large pulls use the **async report-task** endpoints
   (create task → poll → fetch), not the synchronous one; paginate via
   `page`/`page_size`.

## Reference pattern

Follows the [Meta reference pattern](./meta-mapping-template.md): `connector` +
`schema_version`, a `report` spec, a `column_map` (with ops like `parse_date` /
`map_value` / `__constant__` / `flatten_report_row` / `cast_type`), and partner
`taxonomies` that resolve into the canonical taxonomies (empty here — `geo` uses the
canonical taxonomy directly). See
[phase-09.7](../phases/phase-09.7-partner-mapping-taxonomy-templates.md) for the
per-partner template contract and
[phase-09.5](../phases/phase-09.5-partner-connectors-google-dv360-tiktok.md) for
the connector build.
