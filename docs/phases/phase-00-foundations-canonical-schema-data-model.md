# Phase 0 — Foundations, Canonical Schema & Data Model

**Depends on:** — (none) · **Status:** Not started · **MVP:** yes (Phases 0–4)

Read alongside: [`../canonical-schema.md`](../canonical-schema.md),
[`../data-model.md`](../data-model.md), [`../architecture.md`](../architecture.md),
and the cross-cutting requirements (CC-1…CC-8) in [`../build-plan.md`](../build-plan.md).

## Objective

Establish the repo, lock foundational decisions, define the canonical schema and
standard taxonomies, and create the core data model.

## Scope

- **In:** repo scaffolding; canonical schema; standard taxonomies; DB tables;
  tenancy model; config-versioning approach.
- **Out:** any file parsing, UI, AI.

## Functional Requirements

- **P0-1** Define the **Canonical Schema** ([`../canonical-schema.md`](../canonical-schema.md), Appendix A) as machine-readable config (e.g. a versioned JSON/YAML spec the app loads).
- **P0-2** Define **standard taxonomies** (Appendix B) for controlled-vocabulary dimensions (channel, funnel_stage, etc.).
- **P0-3** Create the **data model** ([`../data-model.md`](../data-model.md), Appendix C): tenants, users, files, sheets, mapping_configs, rules, taxonomies, jobs, job_events, output tables.
- **P0-4** Decide **tenant isolation model**: row-level (`tenant_id`) is the default recommendation; document the choice. *(Open Question OQ-0.1.)*
- **P0-5** Establish **config versioning**: mapping configs and rule sets MUST be versioned; older versions retained for traceability.
- **P0-6** Define **environment/config management** and secrets handling (no credentials in code).

## Deliverables

- Repo skeleton (backend service, worker skeleton, frontend skeleton — empty but wired).
- `canonical_schema.yaml` + `taxonomies.yaml` loaded and validated at startup.
- Database migrations for all Phase-0 tables.
- Architecture decisions documented in [`../architecture.md`](../architecture.md) (tenancy, versioning, stack).

## Acceptance Criteria

- App boots, loads and validates the canonical schema + taxonomies.
- All Phase-0 tables exist via migrations; every domain table has `tenant_id`.
- Can create a tenant and a user record scoped to that tenant.
- No hardcoded schema anywhere — it is read from config.

## Dependencies

None.

## Open Questions

- **OQ-0.1** — ✅ Resolved: **row-level isolation** (`tenant_id` on every domain table). See ADR-003.
- **OQ-0.2** — ✅ Resolved: clean output = an **`output_row` table in the backend DB** for v1; dedicated warehouse deferred. See ADR-005. (Also resolves OQ-INIT.2.)

_All Phase-0 open questions resolved. See [`../open-questions.md`](../open-questions.md)._

## Sub-phases

TBD — to be broken down before implementation.
