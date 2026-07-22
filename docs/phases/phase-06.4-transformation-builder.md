# Phase 06.4 — Transformation Builder + Live Preview

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** 06.1,
06.3 · **Status:** Planned. Covers **P6-3**, **P6-4**.

## Objective

Let a user author transformation rules by UI actions (pick a column → choose an
operation → configure) with an immediate before/after preview — never exposing raw
JSON.

## Scope

- **In:** action-based rule builder (operation picker + per-op config forms, e.g.
  collapse distinct raw values to a canonical term); an ordered rule list; live
  before/after preview on sample rows; save rule set.
- **Out:** validation (06.5).

## Functional Requirements

- **P6.4-1** Add a rule by selecting a column + operation and configuring it via
  form controls (no JSON). Each action authors one `RuleSpec`.
- **P6.4-2** Show the ordered rule list; allow reorder/remove.
- **P6.4-3** Live before/after preview via the `/transform/preview` endpoint on
  sample rows, updating on every change (P6-4).
- **P6.4-4** Save the rule set (versioned) via the existing endpoint.

## Deliverables

- Transformation-builder route + components (op picker, config forms, preview table).

## Acceptance Criteria

- A user collapses messy channel values via the UI and sees live before/after;
  saving persists a versioned rule set; no JSON shown.
- `typecheck`/`lint`/`build` pass.

## Dependencies

06.1/06.3; Phase 3 transform preview + rule-set APIs.

## Open Questions

None.

## Sub-phases

N/A (leaf).
