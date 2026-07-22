# Phase 06.2 — Job / File Dashboard

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** 06.1 ·
**Status:** In progress. Covers **P6-1**.

## Objective

Give users a home screen listing their files/jobs with status and per-file
progress, surfacing what needs attention, and letting them upload + process files.

## Scope

- **In:** file/job list with status badges; upload control; process trigger;
  drill-in to a file's sheets; a "needs attention" summary (unmapped / flagged).
- **Out:** the mapping/transform/validation screens (06.3–06.5).

## Functional Requirements

- **P6.2-1** List files with latest job status + sheet counts (uses 06.1 read endpoints).
- **P6.2-2** Upload a file and trigger processing from the UI.
- **P6.2-3** Drill into a file to see its sheets and their status (parsed / needs-review).
- **P6.2-4** Summarize what needs attention (files with unmapped/needs-review sheets or open flags).

## Deliverables

- `app/(dashboard)` route(s) + file/sheet list components + upload.

## Acceptance Criteria

- Uploading a file shows it in the list; processing updates its status + sheets.
- `typecheck`/`lint`/`build` pass.

## Dependencies

06.1; Phase 1 ingest/process APIs.

## Open Questions

None.

## Sub-phases

N/A (leaf).
