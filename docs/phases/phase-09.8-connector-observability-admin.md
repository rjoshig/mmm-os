# Phase 9.8 — Connector Observability & Admin

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** 09.2, 09.6 · **Status:** Deferred (designed).

## Objective

Give operators and customers visibility into connector health — sync status,
last-successful-pull, row counts — and the admin hooks to manage connectors.

## Scope

- **In:** `sync_run` status surfacing (last successful pull, window, row counts,
  errors, timing); connector health/status; admin actions (enable/disable, trigger
  backfill, re-auth); observability (CC-7).
- **Out:** the pull/scheduling engines themselves (09.4/09.5/09.6).

## Functional Requirements

- **P9.8-1** Expose per-connector status: last successful pull, next scheduled run,
  recent `sync_run` outcomes, row counts, and surfaced errors (CC-7).
- **P9.8-2** Admin hooks: enable/disable a connector, trigger a manual sync or
  backfill, and re-authorise credentials (CC-10).
- **P9.8-3** Credential state (valid / expiring / revoked) is visible **without
  exposing secrets** (never logged/displayed).

## Deliverables

- Connector status/observability surface (API + Phase-6 UI hooks).
- Admin actions wired to the connector framework.

## Acceptance Criteria

- An operator can see each connector's last successful pull, row counts, and any
  errors, and can trigger a backfill or re-auth.
- No secret material is ever exposed in status or logs (CC-10).

## Dependencies

09.2 (framework/credentials), 09.6 (sync runs), Phase 6 (UI), Phase 8 (admin/RBAC).

## Open Questions

None beyond the parent's `OQ-9.*`.

## Sub-phases

N/A (leaf sub-phase).
