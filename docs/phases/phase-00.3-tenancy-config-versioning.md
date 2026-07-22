# Phase 0.3 — Tenancy & Config Versioning

**Parent:** [`phase-00`](./phase-00-foundations-canonical-schema-data-model.md) ·
**Depends on:** 00.2 · **Status:** Done (pending PR merge)

Covers Phase-0 requirements **P0-4**, **P0-5**, **P0-6**.

## Objective

Prove the tenancy model end-to-end (create a tenant + a tenant-scoped user) and
establish the config-versioning mechanism for `mapping_config` / `rule_set`, with
secrets handled via env only.

## Scope

- **In:** thin service(s) to create a tenant and a user scoped to it; a
  versioning helper that produces a new version on config change while retaining
  prior versions; confirmation of env-based config/secret handling.
- **Out:** RBAC/auth (Phase 8), mapping/rule authoring (Phases 2/3), API surface
  beyond a minimal create/read.

## Functional Requirements

- **P0.3-1** Create a `tenant`; create a `user` that belongs to that tenant; no operation returns cross-tenant rows (CC-1).
- **P0.3-2** Config versioning: saving a new revision of a `mapping_config`/`rule_set` creates a new `version` and retains prior versions (config-as-data + traceability, CC-4/CC-3).
- **P0.3-3** A tenant-scoped query helper enforces `tenant_id` filtering as the default path.
- **P0.3-4** Confirm environment/secret handling: all config via env (`BACKEND_DATABASE_URL`, future keys), nothing hardcoded (P0-6).

## Deliverables

- `src/mmm_os/` service functions for tenant/user creation + a versioning helper.
- Pydantic v2 schemas (`schemas/`) for the create/read payloads, separate from ORM models.
- Tests: tenant+user creation is tenant-scoped; editing a config yields v2 while v1 remains retrievable.

## Acceptance Criteria

- Can create a tenant and a user record scoped to that tenant.
- Editing a config creates v2; v1 remains retrievable (prior outputs stay traceable to the version used).
- No cross-tenant data is returned by the provided helpers.
- No secrets in code; configuration read from env.

## Dependencies

Phase 0.2.

## Open Questions

OQ-0.1 resolved (row-level). No outstanding blockers.

## Sub-phases

N/A (leaf sub-phase).
