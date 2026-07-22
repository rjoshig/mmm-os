# Phase 06.5 — Validation Review

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** 06.1,
06.2 · **Status:** Planned. Covers **P6-5**.

## Objective

Let a user review validation flags — with location, severity, and AI explanation —
and acknowledge/resolve/override them.

## Scope

- **In:** flag list per job with severity badges + location + AI explanation;
  acknowledge/resolve/override actions; blocked-output indicator.
- **Out:** the mapping/transform screens.

## Functional Requirements

- **P6.5-1** List a job's flags with severity, location (field/row), and message +
  AI explanation where present.
- **P6.5-2** Acknowledge / resolve / override a flag via the review endpoint (P4-5).
- **P6.5-3** Indicate when output is blocked by a BLOCK-severity flag.

## Deliverables

- Validation-review route + components (flag table, severity badges, review controls).

## Acceptance Criteria

- A user reviews and resolves a flag; state updates; blocked output is clearly shown.
- `typecheck`/`lint`/`build` pass.

## Dependencies

06.1/06.2; Phase 4 validation APIs.

## Open Questions

None.

## Sub-phases

N/A (leaf).
