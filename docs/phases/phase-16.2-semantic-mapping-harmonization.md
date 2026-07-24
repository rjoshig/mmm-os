# Phase 16.2 — Semantic Mapping & Harmonization Engine

**Parent:** [`phase-16-harmonization-stack-assembly.md`](./phase-16-harmonization-stack-assembly.md)
· **Status:** Build · **Cycle:** 5

Cross-cutting: config-as-data (CC-4), traceability (CC-3), semantic integrity (CC-15).

## Objective

Unify multiple Silver outputs into one coherent panel by resolving the differences
between sources — taxonomy, field semantics, currency/timezone/attribution, and
entity naming — as **versioned config**, distinct from Stage-1 per-source column
mapping.

## Functional Requirements

- **P16.2-1 Harmonization rule set** — a versioned, layered (global → template →
  customer) config family for cross-source harmonization (a separate family from
  Stage-1 `RuleSet`, per OQ-16.2). Ordered, declarative, previewable.
- **P16.2-2 Taxonomy/value harmonization** — map divergent source values to the
  canonical taxonomy (Meta "FB" / Google "Facebook" → `meta`), reusing
  `Taxonomy` / `TaxonomyAlias`.
- **P16.2-3 Semantic field mapping** — map source-specific fields to canonical
  fields across sources (`link_clicks` → `clicks`), including tenant-extension
  fields from the resolved schema (Phase 21).
- **P16.2-4 Frame reconciliation** — convert currency to the reporting currency
  (via `tenant_settings` FX), normalize timezone, and align attribution window to
  a consistent policy.
- **P16.2-5 Entity resolution** — reconcile campaign/geo/product naming across
  sources (attribute-align → block → link → canonicalize); deterministic
  alias-table first, with the residual left for AI assist (Phase 16.3).
- **P16.2-6 Preview** — live before/after on sample rows (reuse `CompactPreview`),
  no writes.

## Acceptance Criteria

- Two sources with different channel spellings and currencies resolve to one
  canonical taxonomy and one reporting currency in the assembled panel.
- Harmonization is stored as versioned config; changing it and re-previewing shows
  the effect without touching stored data.
- A source field renamed via the semantic map lands in the correct canonical (or
  tenant-extension) column, traceable to its source (CC-3).

## Dependencies

Phase 16.1 (Stack/assembly), Phase 21 (resolved schema for extension targets).

## Open Questions

Inherits parent OQ-16.2, OQ-16.3.
