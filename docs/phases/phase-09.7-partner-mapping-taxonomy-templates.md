# Phase 9.7 — Partner Mapping & Taxonomy Templates

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.4, Phase 2 · **Status:** Deferred (designed).

## Objective

Because partner API schemas are **stable**, ship **default column→canonical
mappings and taxonomy defaults** per connector so partner data auto-maps with
minimal human review — reusing the Phase-2 template layer.

**Worked reference example:** the Meta template is the canonical pattern —
[`docs/connectors/meta-mapping-template.md`](../connectors/meta-mapping-template.md)
+ [`src/mmm_os/connectors/meta/templates/default_mapping.yaml`](../../src/mmm_os/connectors/meta/templates/default_mapping.yaml).
Every other partner (Google Ads, DV360, TikTok) ships an equivalent
`default_mapping.yaml` following the same shape.

## The per-partner template contract

Each connector MUST provide a `default_mapping.yaml` with:

- **`connector` + `schema_version`** — identity + versioning of the template.
- **`default_breakdowns`** — the report breakdowns pulled by default (each adds
  rows + API cost — a deliberate choice, not free).
- **Attribution / config defaults** — e.g. `attribution_windows`; pinned defaults
  that must stay consistent across pulls (they change the numbers).
- **`column_map`** — canonical field ← partner source field, with **ops** for
  fields that are not a direct column map: `parse_date` (dates), `map_value`
  (taxonomy normalization), a `__constant__` source (fixed values like
  `channel: "Facebook"`), and **`extract_action`** for **nested** metrics
  (conversions/revenue that live inside arrays keyed by `action_type`).
- **`taxonomies`** — partner-specific source-value maps (e.g.
  `meta_publisher_platform`, `meta_objective_to_funnel`) that resolve **into** the
  canonical taxonomies (Appendix B).

## Scope

- **In:** per-partner default mapping templates (e.g. Meta `spend` → canonical
  `spend`) and taxonomy defaults (e.g. platform → `Facebook`); registration into
  the Phase-2 template layer; still human-ratifiable (CC-5).
- **Out:** the per-partner pull logic (09.4/09.5).

> **Transform-engine dependency:** nested metrics need an **`extract_action`**
> operation (pull the value for a chosen `action_type` from an `actions` /
> `action_values` array). This is a partner-specific need the Phase-3 operation
> library must support — tracked as an open item on
> [phase-03](./phase-03-transformation-rule-engine.md).

## Functional Requirements

- **P9.7-1** Each connector ships a **default `mapping_config` template** at the
  `template` layer (customer overrides still win — config-as-data, CC-4).
- **P9.7-2** Each connector ships **taxonomy defaults** collapsing partner values
  to canonical terms.
- **P9.7-3** Applied automatically for that source, but **surfaced for human
  accept/reject** (CC-5) — never silently committed.

## Deliverables

- Per-partner template packs registered in the Phase-2 template layer.

## Acceptance Criteria

- A partner pull auto-maps its known columns via the default template, requiring
  minimal review; a customer override still takes precedence.
- Taxonomy defaults collapse partner platform/label values to canonical terms.
- **Meta reference:** a Meta pull, run through its default template, yields
  canonical rows with correct `channel`/`sub_channel`/`geo`, **extracted**
  `conversions` & `revenue` (via `extract_action`), and `currency` — with **zero
  manual mapping for the standard case**.

## Dependencies

Phase 2 (mapping + taxonomy template layer), 09.4 (first partner).

## Open Questions

OQ-9.7 (currency/timezone normalisation source of truth).

## Sub-phases

N/A (leaf sub-phase).
