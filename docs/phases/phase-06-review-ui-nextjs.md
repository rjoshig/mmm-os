# Phase 6 — Review UI (Next.js)

**Depends on:** Phases 2–5 (+ **00.5 auth**, per the build order) · **Status:** In progress

The UI shell is scaffolded during repo initialization; feature screens land here.
All UI MUST match the design language in [`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md).

> **Auth seam (interim).** The authoritative build order puts **00.5 Authentication**
> before Phase 6 (CC-11). 00.5 is not built yet, so this phase ships a **tenant/auth
> seam** — a single provider (`lib/tenant.ts`) that supplies the active `tenant_id`
> to every API call. When 00.5 lands, it replaces the seam's source (a real
> session) **without touching the screens**. This is a deliberate, temporary
> deviation to deliver the UI now; the retrofit surface is one module.
>
> **Backend read endpoints.** The dashboard/mapping screens need tenant-scoped
> **GET/list** endpoints that Phases 1–5 did not add (they exposed only
> POST/actions). Phase 6 adds thin read routes (list files+jobs, file detail with
> sheets, sheet detail with profile) following the existing router patterns.

## Objective

Give users an intuitive, preview-driven interface to review AI suggestions,
confirm mappings, tune transformations, and resolve validation flags —
**generating config behind the scenes** (users never write JSON).

## Scope

- **In:** file/job dashboard; mapping-review screen; transformation builder
  (action-based); validation-review screen; before/after preview everywhere.
- **Out:** connector config UI, admin/RBAC UI (Phase 8).

## Functional Requirements

- **P6-1 Job dashboard:** list files/jobs with status, per-file progress, and what needs attention.
- **P6-2 Mapping review:** show source columns + samples alongside AI-suggested canonical fields (with confidence + reason); user accepts/rejects/modifies. Actions write mapping config.
- **P6-3 Action-based transformation builder:** user clicks a column → picks an operation → configures via UI (e.g. assign canonical values to distinct raw values); each action authors a rule. **No raw JSON exposed.**
- **P6-4 Live preview:** every mapping/rule change shows before/after on sample rows immediately.
- **P6-5 Validation review:** list flags with location + severity + AI explanation; acknowledge/resolve/override.
- **P6-6 Reuse visibility:** show when a saved config auto-applied, and let the user confirm or adjust.

## Deliverables

- Next.js app implementing the four screens above against the Phase 1–5 APIs.

## Acceptance Criteria

- A non-technical user can, without seeing any JSON: upload a file, review/accept AI mapping suggestions, collapse messy channel values via the UI, see live before/after, resolve a flag, and produce clean output.
- Editing anything updates the underlying versioned config correctly.
- Auto-applied configs are clearly indicated.

## Dependencies

Phases 2–5.

## Open Questions

- **OQ-6.1** — ✅ Resolved: **extracted design tokens + hand-built shadcn-style
  primitives** (Card/Badge/Table/PageHeader/StatCard); no heavy third-party
  component library. See ADR-009 and [`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md).
  A component library can still be layered later if needed.

_Phase-6 open question resolved. See [`../open-questions.md`](../open-questions.md)._

## Sub-phases

- [`phase-06.1-ui-foundation.md`](./phase-06.1-ui-foundation.md) — design primitives, typed API client, tenant/auth seam, app shell + backend read endpoints (P6 infra).
- [`phase-06.2-job-dashboard.md`](./phase-06.2-job-dashboard.md) — file/job dashboard + upload + what-needs-attention (P6-1).
- [`phase-06.3-mapping-review.md`](./phase-06.3-mapping-review.md) — mapping review with AI suggestions; accept/reject/modify writes config (P6-2, P6-6).
- [`phase-06.4-transformation-builder.md`](./phase-06.4-transformation-builder.md) — action-based rule authoring with live before/after preview (P6-3, P6-4).
- [`phase-06.5-validation-review.md`](./phase-06.5-validation-review.md) — validation flags with severity + AI explanation; acknowledge/resolve/override (P6-5).
