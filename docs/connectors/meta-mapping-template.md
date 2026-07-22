# Meta (Facebook/Instagram) — Default Mapping Template

This is the **worked reference example** of a partner default mapping template. It
maps Meta Marketing API *Insights* fields onto the [canonical schema](../canonical-schema.md)
and **auto-applies on every Meta connector pull**, so standard Meta data lands as
canonical rows with **zero manual mapping** for the common case. It is
config-as-data (CC-4): the machine-readable source is
[`src/mmm_os/connectors/meta/templates/default_mapping.yaml`](../../src/mmm_os/connectors/meta/templates/default_mapping.yaml).
Like all mapping config it sits at the **`template` layer** of the Phase-2 layered
config, so a tenant may **override any field per tenant** (customer overrides win).
Every other partner (Google Ads, DV360, TikTok) ships an equivalent
`default_mapping.yaml` following this same shape.

> **Provisional field names.** The exact Meta field names, breakdown keys, and
> attribution parameters below are treated as **provisional** and MUST be confirmed
> against the live Marketing API version when Phase 09.4 is implemented (OQ-9.x).

## Mapping table

| Canonical field | Meta source field | Notes |
|---|---|---|
| `date` | `date_start` | `parse_date` → ISO date. |
| `channel` | *(constant)* `"Facebook"` | Fixed per connector; placement carried in `sub_channel`. See design note. |
| `sub_channel` | `publisher_platform` | `map_value` via `meta_publisher_platform` taxonomy (facebook/instagram/audience_network/messenger). |
| `campaign` | `campaign_name` | Direct. |
| `ad_group` | `adset_name` | Meta "ad set" == canonical `ad_group`. |
| `geo` | `country` | `map_value` via canonical `geo` taxonomy. |
| `product` | *(none)* | Not available from Meta; left null. |
| `funnel_stage` | `objective` | **Derived** via `meta_objective_to_funnel` taxonomy; best-effort, optional. |
| `spend` | `spend` | In `account_currency`. |
| `impressions` | `impressions` | Direct. |
| `clicks` | `inline_link_clicks` | Defaults to **link** clicks (not all-clicks); overridable. |
| `reach` | `reach` | Direct. |
| `conversions` | `actions[]` | **Nested** — `extract_action` with `action_type: purchase` (per-tenant). |
| `revenue` | `action_values[]` | **Nested** — `extract_action` with `action_type: purchase` (per-tenant). |
| `currency` | `account_currency` | Drives downstream `convert_currency` if normalizing. |

## Three important nuances

1. **Conversions & revenue are nested, not columns.** Meta returns them inside the
   `actions` and `action_values` arrays, keyed by `action_type` (e.g. `purchase`,
   `lead`, or a custom conversion). They cannot be direct-mapped — they need an
   `extract_action` transform that pulls the value for a chosen `action_type`.
   **Which `action_type` counts as "the" conversion is a per-tenant decision**
   (one advertiser's KPI is purchases, another's is leads), so it is a template/
   tenant config value, not a fixed mapping.

2. **Attribution windows change the numbers.** The *same* campaign reports
   *different* conversions and revenue under different attribution settings (e.g.
   `7d_click` vs `1d_view`). The template pins a default
   (`attribution_windows: ["7d_click", "1d_view"]`), but it **must be consistent
   across pulls** and **confirmed with the customer**, because it materially
   changes the numbers fed into the model. Changing it mid-history creates
   apparent (but false) trend shifts.

3. **Breakdowns multiply rows and API cost.** Each breakdown
   (`publisher_platform`, `country`, …) multiplies row cardinality and API quota
   usage. The template declares its default breakdowns explicitly
   (`publisher_platform`, `country`); **adding more is a deliberate config choice**
   with a cost/cardinality trade-off, not a free default.

## Modeling choices

- **`channel` is fixed to `"Facebook"`**, with the specific placement carried in
  `sub_channel` (from `publisher_platform`). **Design decision / alternative:** one
  could instead *derive* `channel` from `publisher_platform` (so Instagram rows get
  `channel = Instagram`). We fix `channel` per connector and keep placement in
  `sub_channel` so all Meta-sourced spend rolls up under one top-level channel;
  a tenant that models Instagram as its own channel can override this.
- **`product` is unavailable from Meta** and is left null; it typically comes from a
  file source (sales/CRM) joined downstream.
- **`funnel_stage` is derived**, best-effort, from the campaign `objective` via the
  `meta_objective_to_funnel` taxonomy. Objectives don't map cleanly to funnel
  stages for every advertiser, so treat it as a hint, not ground truth; it is
  optional and overridable.

## Reference pattern

This Meta template is the **canonical pattern** every other partner follows. Each
connector (Google Ads, DV360, TikTok) ships its own `default_mapping.yaml` with the
same structure — `connector`, `schema_version`, `default_breakdowns`, attribution/
config defaults, a `column_map` (using ops like `parse_date` / `map_value` /
`extract_action` for nested and derived fields), and partner-specific `taxonomies`
that resolve into the canonical taxonomies. See
[phase-09.7](../phases/phase-09.7-partner-mapping-taxonomy-templates.md) for the
per-partner template contract.
