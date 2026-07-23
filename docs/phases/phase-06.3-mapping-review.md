# Phase 06.3 — Mapping Review

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** 06.1,
06.2 · **Status:** Done (+ Cycle-1 UX overhaul: value-profile mapping). Covers **P6-2**, **P6-6**.

## Objective

Let a user review a sheet's source columns against AI-suggested canonical fields
and accept/reject/modify — authoring the mapping config without seeing JSON.

## Scope

- **In:** per-sheet column list with **value profile** (distinct sample values,
  distinct count, null rate); AI suggestion (canonical field + confidence +
  rationale) per column; **accept/reject per suggestion + "accept all
  high-confidence"**; **searchable canonical-field picker**; **live required-field
  coverage meter**; save mapping; auto-applied-config indicator (P6-6).
- **Out:** transformation rules (06.4).

## Functional Requirements

- **P6.3-1** Show each source column with type + **value profile** (distinct
  samples, distinct count, null rate) from the sheet profile — so users map from
  real data, not just headers.
- **P6.3-2** Request + show AI mapping suggestions (confidence + reason) as
  **proposals** (suggest-not-decide, CC-5); the LLM being disabled degrades
  gracefully (clear message, manual mapping still works).
- **P6.3-3** **Accept/reject each proposal** and **"Accept all high-confidence"
  (≥ 0.85)**; accepting writes the column→field choice (committed on Save).
- **P6.3-4** Indicate when a saved config auto-applied (via automap) and let the
  user confirm/adjust (P6-6).
- **P6.3-5** **Searchable canonical-field picker** (`components/ui/searchable-select.tsx`)
  for the target schema.
- **P6.3-6** **Live coverage meter** (`components/coverage-meter.tsx`): required
  canonical fields satisfied vs missing, computed from the current (unsaved) mapping.

## Deliverables

- Mapping-review route + components: column table with value profiles, suggestion
  accept/reject + accept-all-high-conf, searchable picker, coverage meter.

## Acceptance Criteria

- A user maps a sheet by reviewing value profiles, accepting/adjusting AI
  proposals (individually or all high-confidence); no JSON shown; config is
  written and versioned.
- The coverage meter reflects required-field satisfaction live as choices change.
- `typecheck`/`lint`/`build` pass.

## Dependencies

06.1/06.2; Phase 2 mapping + Phase 5 AI APIs.

## Open Questions

None.

## Sub-phases

N/A (leaf).
