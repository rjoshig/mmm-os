# Phase 3.2 — Value Operations, Escape Hatch, Preview & API

**Parent:** [`phase-03`](./phase-03-transformation-rule-engine.md) ·
**Depends on:** 03.1 · **Status:** Done (pending PR merge)

Covers **P3-2 (value ops), P3-3, P3-6, P3-7, P3-8**.

## Objective

Add the value/domain operations (including taxonomy harmonisation), the sandboxed
`custom` escape hatch, the before/after preview service, and versioned rule-set
persistence exposed via the API.

## Scope

- **In:** `map_value` (taxonomy harmonisation), `parse_date`, `convert_currency`,
  `reshape` (wide→long); `custom` sandboxed-expression op (ADR-004); preview
  (before/after on sample rows, no persistence); versioned `rule_set`/`rule`
  persistence + layered resolution; API.
- **Out:** validation/anomaly (Phase 4); UI (Phase 6); AI (Phase 5).

## Functional Requirements

- **P3.2-1 Value ops:** `parse_date`, `convert_currency`, `reshape` (wide→long, OQ-3.2 config model), plus `map_value`.
- **P3.2-2 Taxonomy harmonisation (P3-6):** `map_value` collapses raw values to canonical taxonomy terms (e.g. `FB`,`fb_ads` → `Facebook`) using the loaded taxonomies.
- **P3.2-3 Escape hatch (P3-3, ADR-004):** a `custom` op evaluating a **sandboxed expression** over the row — allowlisted operators/functions only, no attribute access, imports, or I/O; resource-bounded.
- **P3.2-4 Preview (P3-7):** given a rule set + sample rows, return before/after **without persisting**.
- **P3.2-5 Versioning (P3-8):** rule sets are versioned; outputs are traceable to the rule-set version applied.
- **P3.2-6 API:** save a rule set (versioned), resolve layered rules, and preview.

## Deliverables

- `transform/operations_value.py`, `transform/operations_custom.py`, `transform/preview.py`, `transform/service.py`.
- `schemas/transform.py` + `api/routers/transform.py`.
- Tests: each value op; taxonomy collapse; sandbox allows safe / blocks unsafe expressions; preview before/after without writes; deterministic/idempotent re-run; versioned save.

## Acceptance Criteria

- A `map_value` rule collapses 3 raw channel spellings to one canonical value.
- `parse_date` + `convert_currency` + `dedupe` apply in order, deterministically.
- Preview returns correct before/after on sample rows without writing anything.
- Re-running the same rule-set version yields identical output (idempotent).
- The `custom` sandbox evaluates allowed expressions and rejects disallowed ones.

## Dependencies

Phase 3.1.

## Open Questions

OQ-3.1 resolved (sandboxed expression); OQ-3.2 resolved (reshape config model).

## Sub-phases

N/A (leaf sub-phase).
