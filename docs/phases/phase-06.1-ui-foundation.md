# Phase 06.1 — UI Foundation (primitives, API client, tenant seam, shell)

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** Phases
2–5, front-end shell · **Status:** In progress.

## Objective

Lay the front-end foundation every feature screen builds on: hand-built design
primitives (ADR-009), a typed API client, the tenant/auth seam, the app shell
(sidebar), and the thin backend **read** endpoints the UI needs.

## Scope

- **In:** `components/ui/*` primitives (Card, Badge, Button, Table, PageHeader,
  StatCard, EmptyState); `lib/api/*` (typed fetch client + response types);
  `lib/tenant.ts` (auth seam); sidebar + layout; backend GET/list routes.
- **Out:** the feature screens themselves (06.2–06.5).

## Functional Requirements

- **P6.1-1** Design primitives use semantic tokens only (no hardcoded colors),
  merged via `cn()` — match `front-end/CLAUDE.md`.
- **P6.1-2** A typed API client reads the backend base URL from env
  (`NEXT_PUBLIC_API_BASE_URL`), injects the active `tenant_id`, and surfaces
  errors (incl. 503 when the LLM is disabled).
- **P6.1-3** A `lib/tenant.ts` seam provides the active tenant; **00.5 replaces its
  source without changing callers** (CC-11 interim).
- **P6.1-4** App shell: sidebar nav (Dashboard, and per-file Mapping/Transform/
  Validation are reached by drill-in) + themed layout.
- **P6.1-5** Backend read endpoints (tenant-scoped, following existing routers):
  list files (+ latest job status), file detail (+ sheets), sheet detail (+
  profile). Keep the backend test suite green.

## Deliverables

- `front-end/components/ui/*`, `front-end/lib/api/*`, `front-end/lib/tenant.ts`,
  updated `app/layout.tsx` + sidebar.
- Backend read routes + a couple of tests.

## Acceptance Criteria

- `npm run typecheck`, `npm run lint`, `npm run build` pass.
- Read endpoints return tenant-scoped data; backend `pytest` stays green.

## Dependencies

Phases 1–5 APIs; ADR-009 design system.

## Open Questions

Auth seam is interim pending Phase 00.5 (CC-11).

## Sub-phases

N/A (leaf).
