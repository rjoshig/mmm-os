# Phase 9.7 — Partner Mapping & Taxonomy Templates

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.4, Phase 2 · **Status:** Deferred (designed).

## Objective

Because partner API schemas are **stable**, ship **default column→canonical
mappings and taxonomy defaults** per connector so partner data auto-maps with
minimal human review — reusing the Phase-2 template layer.

## Scope

- **In:** per-partner default mapping templates (e.g. Meta `spend` → canonical
  `spend`) and taxonomy defaults (e.g. platform → `Facebook`); registration into
  the Phase-2 template layer; still human-ratifiable (CC-5).
- **Out:** the per-partner pull logic (09.4/09.5).

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

## Dependencies

Phase 2 (mapping + taxonomy template layer), 09.4 (first partner).

## Open Questions

OQ-9.7 (currency/timezone normalisation source of truth).

## Sub-phases

N/A (leaf sub-phase).
