# Phase 20 — Dashboard Revamp + Live Pipeline Monitoring

**Depends on:** 6 (UI), 07.1 (observability), 13 (runs history), 16 (Stacks)
· **Status:** Build · **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: observability (CC-7), multi-tenant (CC-1).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §4.7.

## Objective

Make pipeline runs **watchable live** and give tenants an **analytics/KPI
dashboard** beyond the current per-file operational view.

## Scope

- **In:** live auto-refresh of in-flight jobs/syncs in the runs view; a tenant-level
  KPI/analytics dashboard.
- **Out:** external alerting/paging stacks (Phase 07.1 owns the metrics backend); a
  full BI tool (this is an operational dashboard, not ad-hoc analytics).

## Cross-cutting

- **CC-7** the live view reads the existing `job_event` timeline + `GET /jobs/{id}`;
  no new observability model is introduced.
- **CC-1** all dashboard aggregates are tenant-scoped.

## Functional Requirements

- **P20-1 Live monitoring** — the runs view (`app/runs/page.tsx`,
  `components/pipeline-stepper.tsx`) auto-refreshes in-flight jobs/syncs via polling
  (or SSE), so a running pipeline updates live (status, per-stage timeline,
  duration, retries). Reuse `job_event` + `GET /jobs/{id}`; stop polling on
  terminal state.
- **P20-2 KPI/analytics dashboard** — a tenant-level rollup: stacks published,
  data-quality trend, open flags by severity, files processed over time, failures
  over time, connector sync health. Reuse `stat-card.tsx` + `data-quality-score.tsx`.
- **P20-3 Charts** — trend visualizations per the Phase-17 charting decision
  (bespoke SVG vs a library, under the design system).
- **P20-4 Drill-through** — dashboard tiles link to the underlying runs / files /
  stacks / flags.

## Deliverables

- Live auto-refresh on the runs view (polling/SSE), terminal-state aware.
- A tenant KPI dashboard with drill-through.
- Dashboard aggregate endpoints (tenant-scoped), reusing existing job/flag/stack
  data.
- Tests: live view reflects a job progressing through stages; dashboard aggregates
  are correct and tenant-isolated.

## Acceptance Criteria

- Starting a pipeline run and watching the runs view shows stages advancing
  **without a manual refresh**; polling stops when the job finishes.
- The dashboard shows stacks-published, data-quality trend, open-flags-by-severity,
  and sync health for the current tenant only; tiles drill through to detail.
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phase 6, Phase 07.1 (metrics/events), Phase 13 (runs history), Phase 16 (Stacks),
Phase 17 (data-quality/flag data + charting decision).

## Open Questions

- **OQ-20.1** live transport — polling (simple, reuses REST) vs SSE (push). Default:
  polling with a short interval on active runs; SSE if latency demands it.

## Sub-phases

TBD (per the sub-phase convention in [`README.md`](./README.md)).
