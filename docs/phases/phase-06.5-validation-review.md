# Phase 06.5 — Validation Review

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** 06.1,
06.2 · **Status:** Done (Cycle-1 UX overhaul: clustered flags + bulk resolve +
data-quality score). Covers **P6-5**.

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
- **P6.5-4** (Cycle 1) Cluster similar flags by `location.check` + field (e.g.
  "3 rows: missing 'channel'") and **bulk-resolve** a whole cluster in one call via
  `POST /jobs/{job_id}/validation-flags/bulk-review`; each cluster expands to its
  individual rows for granular review. Stale/foreign flag ids are ignored server-side.
- **P6.5-5** (Cycle 1) Headline **data-quality score** — the severity-weighted share
  of flags cleared (resolved/overridden) — that rises as clusters are resolved, with
  an open-issue breakdown by severity. (AI-remediation suggestions per flag are
  Cycle 4.)

## Deliverables

- Validation-review route + components: `data-quality-score.tsx` (headline metric),
  `validation/flag-clusters.tsx` (clustered flags + bulk/per-row review controls).
- Backend `review_flags_bulk` service + bulk-review endpoint + schemas.

## Acceptance Criteria

- A user reviews and resolves a flag; state updates; blocked output is clearly shown.
- Hundreds of similar flags collapse into a handful of clusters; resolving a cluster
  clears all its open flags at once and raises the data-quality score.
- `typecheck`/`lint`/`build` pass; backend `ruff`/`mypy`/`pytest` pass
  (`test_bulk_review_resolves_a_cluster`, `test_bulk_review_unknown_job_404`).

## Dependencies

06.1/06.2; Phase 4 validation APIs.

## Open Questions

None.

## Sub-phases

N/A (leaf).
