# Phase 6 — Review UI (Next.js)

**Depends on:** Phases 2–5 (+ **00.5 auth**, per the build order) · **Status:** Done (all sub-phases implemented; pending PR merge); **UX overhaul in progress (Cycle 1)** — see "UX overhaul" below.

The UI shell is scaffolded during repo initialization; feature screens land here.
All UI MUST match the design language in [`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md).

> **Auth.** Phase 00.5 (Authentication) is **Done**; the UI authenticates via the
> session in `lib/session.ts` and scopes every call to the session's tenant
> (`lib/tenant.ts`). `NEXT_PUBLIC_AUTH_ENABLED` gates the client-side login
> redirect to match the backend's `AUTH_ENABLED`.
>
> **Backend read endpoints.** The dashboard/mapping screens need tenant-scoped
> **GET/list** endpoints that Phases 1–5 did not add (they exposed only
> POST/actions). Phase 6 adds thin read routes (list files+jobs, file detail with
> sheets, sheet detail with profile, real-data sheet rows, canonical fields,
> per-file **pipeline status**) following the existing router patterns.

## Objective

Give users an intuitive, preview-driven interface to review AI suggestions,
confirm mappings, tune transformations, and resolve validation flags —
**generating config behind the scenes** (users never write JSON).

## Scope

- **In:** file/job dashboard; mapping-review screen; transformation builder
  (action-based); validation-review screen; **output generation**; **full-pipeline
  run**; before/after preview everywhere.
- **Out:** connector config UI (Phase 9/Cycle 3). Admin/RBAC UI is delivered in
  Phase 8 (admin console: users, audit log, access review).

## Functional Requirements

- **P6-1 Job dashboard:** list files/jobs with status, per-file progress, and what needs attention.
- **P6-2 Mapping review:** show source columns + samples alongside AI-suggested canonical fields (with confidence + reason); user accepts/rejects/modifies. Actions write mapping config.
- **P6-3 Action-based transformation builder:** user clicks a column → picks an operation → configures via UI (e.g. assign canonical values to distinct raw values); each action authors a rule. **No raw JSON exposed.**
- **P6-4 Live preview:** every mapping/rule change shows before/after on sample rows immediately.
- **P6-5 Validation review:** list flags with location + severity + AI explanation; acknowledge/resolve/override.
- **P6-6 Reuse visibility:** show when a saved config auto-applied, and let the user confirm or adjust.
- **P6-7 Output generation:** from the validation screen, generate clean, traceable
  output rows (`POST /jobs/{id}/sheets/{sid}/generate-output`, gated on no open
  blocking flags; `force=true` override) and preview the result
  (`GET /jobs/{id}/output`).
- **P6-8 Full-pipeline run:** one action on the file-detail screen runs
  detect→map→transform→validate→output per sheet
  (`POST /files/{id}/run-pipeline`), the single call an external scheduler drives.
- **P6-9 Pipeline stepper:** file detail shows each sheet's stage
  (Ingested→Mapped→Transformed→Validated→Ready) via `GET /files/{id}/pipeline-status`,
  with the next incomplete step one click away.

## Deliverables

- Next.js app implementing the screens above against the Phase 1–5 (+output/pipeline) APIs.

## Acceptance Criteria

- A non-technical user can, without seeing any JSON: upload a file, review/accept AI mapping suggestions, collapse messy channel values via the UI, see live before/after, resolve a flag, and produce clean output.
- Editing anything updates the underlying versioned config correctly.
- Auto-applied configs are clearly indicated.
- A user can run the full pipeline from the file-detail screen and see clean output
  generated (or a per-sheet "needs mapping" / "blocked" status).

## UX overhaul (Cycle 1 — in progress)

The platform is being upgraded from an interactive MVP to an enterprise UX (see
`~/.claude/plans/ok-so-yes-i-swift-micali.md`). Cycle 1 deliverables landing in
Phase 6:

- ✅ **Pipeline stepper** (`components/pipeline-stepper.tsx`) + `pipeline-status`
  endpoint — orienting per-sheet stage with next-action links.
- ✅ **Value-profile-driven mapping** (distinct values + sample per column), inline
  AI accept/reject + "accept all high-confidence", searchable canonical-field
  picker, live coverage meter.
- ✅ **Transform builder — full operation set + signature-scoped reuse**: the UI now
  exposes all 10 operations (added `convert_currency`, `dedupe`, `reshape`, `custom`
  editors), and rule sets are keyed by **column signature** (`sig:…`), not `sheet-{id}`,
  via new `GET`/`POST /sheets/{sheet_id}/rule-set` endpoints — so a rule set saved on one
  sheet is reused by any file with identical headers ("configure once, reuse forever").
  Backend `resolve_rule_specs`/output/validation/pipeline-status all resolve by signature.
- ⏳ **Clustered validation flags** with bulk resolve + data-quality score.
- ⏳ **Guided add-source wizard** + design-system polish (skeletons, toasts).

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
