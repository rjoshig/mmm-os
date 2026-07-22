# Google Ads — Default Mapping Template

Maps Google Ads API (GAQL reporting) fields onto the
[canonical schema](../canonical-schema.md) and **auto-applies on every Google Ads
connector pull**, so standard data lands as canonical rows with **zero manual
mapping** for the common case. It is config-as-data (CC-4); the machine-readable
source is
[`src/mmm_os/connectors/google_ads/templates/default_mapping.yaml`](../../src/mmm_os/connectors/google_ads/templates/default_mapping.yaml).
It sits at the **`template` layer** of the Phase-2 layered config, so a tenant may
**override any field per tenant** (customer overrides win). It follows the
[Meta reference pattern](./meta-mapping-template.md); see also the
[DV360 template](./dv360-mapping-template.md).

> **Provisional field names.** The exact GAQL field/metric names and conversion
> params below are **provisional** and MUST be confirmed against the live Google
> Ads API version when Phase 09.5 is implemented (OQ-9.x).

## Mapping table

| Canonical field | Google Ads source | Notes |
|---|---|---|
| `date` | `segments.date` | `parse_date` → ISO date. |
| `channel` | *(constant)* `"Google"` | Fixed per connector; network in `sub_channel`. |
| `sub_channel` | `campaign.advertising_channel_type` | `map_value` via `google_channel_type` (Search/Display/YouTube/Shopping/PMax/Demand Gen). |
| `campaign` | `campaign.name` | Direct. |
| `ad_group` | *(none at campaign level)* | Set when pulling the `ad_group` resource. |
| `geo` | `geographic_view.country_criterion_id` | **ID, not a name** → `resolve_geo_target` to a country; separate `geographic_view` pull. |
| `product` | *(none)* | Not from Google Ads reporting. |
| `funnel_stage` | *(none)* | Not reliably derivable; optional. |
| `spend` | `metrics.cost_micros` | **In micros** → `micros_to_currency` (÷ 1,000,000). |
| `impressions` | `metrics.impressions` | Direct. |
| `clicks` | `metrics.clicks` | Direct. |
| `conversions` | `metrics.conversions` | Depends on the customer's chosen `conversion_action`(s). |
| `revenue` | `metrics.conversions_value` | Value of counted conversions. |
| `reach` | *(none)* | Google Ads has no native reach. |
| `currency` | `customer.currency_code` | Account currency; drives `convert_currency` if normalizing. |

## Key nuances

1. **Cost is in micros.** `metrics.cost_micros` is account currency × 1,000,000, so
   it must be divided by 1,000,000 via a dedicated `micros_to_currency` op — a
   direct map would be off by six orders of magnitude.
2. **GAQL query model.** Reporting is `SELECT metrics/segments FROM <resource>`; the
   **resource sets granularity** and there are **field-compatibility rules** (not
   all metrics/segments combine). Because of this, **geo needs a separate
   `geographic_view` pull** rather than being a breakdown on the campaign query.
3. **Geo is an ID, not a name.** `geographic_view.country_criterion_id` is a
   geo-target-constant **ID** that must be resolved to a country (`resolve_geo_target`
   op) before mapping into the canonical `geo` taxonomy.
4. **Conversions are customer-configured.** Which `conversion_action`(s) count as
   "the" conversion is a **per-tenant decision** (parallels Meta's `action_type`).
   `conversions` and `all_conversions` also differ (the latter includes
   cross-device/view-through per settings) — pick deliberately.
5. **API data is deduped and may not match the Google Ads UI.** Small
   discrepancies between the reporting API and the UI are **expected** (different
   dedup/attribution surfaces); document it so it isn't mistaken for a bug.
6. **No native reach.** Unlike Meta/TikTok, Google Ads does not report reach here;
   `reach` is left null.

## Reference pattern

Follows the [Meta reference pattern](./meta-mapping-template.md): `connector` +
`schema_version`, a `report`/query spec, a `column_map` (with ops like
`parse_date` / `map_value` / `__constant__` / `micros_to_currency` /
`resolve_geo_target`), and partner `taxonomies` that resolve into the canonical
taxonomies. See
[phase-09.7](../phases/phase-09.7-partner-mapping-taxonomy-templates.md) for the
per-partner template contract and
[phase-09.5](../phases/phase-09.5-partner-connectors-google-dv360-tiktok.md) for
the connector build.
