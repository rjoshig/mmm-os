# Phase 06.3 — Mapping Review

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** 06.1,
06.2 · **Status:** Planned. Covers **P6-2**, **P6-6**.

## Objective

Let a user review a sheet's source columns against AI-suggested canonical fields
and accept/reject/modify — authoring the mapping config without seeing JSON.

## Scope

- **In:** per-sheet column list with sample values; AI suggestion (canonical field
  + confidence + rationale) per column; accept/reject/modify; save mapping;
  auto-applied-config indicator (P6-6).
- **Out:** transformation rules (06.4).

## Functional Requirements

- **P6.3-1** Show each source column with type + samples (from the profile).
- **P6.3-2** Request + show AI mapping suggestions (confidence + reason); the LLM
  being disabled degrades gracefully (clear 503 message, manual mapping still works).
- **P6.3-3** Accept/reject/modify a suggestion; accept writes the mapping config
  (a human action, CC-5) via the existing accept endpoint or save-mapping.
- **P6.3-4** Indicate when a saved config auto-applied (via automap) and let the
  user confirm/adjust (P6-6).

## Deliverables

- Mapping-review route + components (column table, suggestion controls).

## Acceptance Criteria

- A user maps a sheet by accepting/adjusting suggestions; no JSON shown; config is
  written and versioned.
- `typecheck`/`lint`/`build` pass.

## Dependencies

06.1/06.2; Phase 2 mapping + Phase 5 AI APIs.

## Open Questions

None.

## Sub-phases

N/A (leaf).
