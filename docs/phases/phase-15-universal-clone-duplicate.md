# Phase 15 — Universal Clone / Duplicate

**Depends on:** 2 (configs), 3 (rule sets), 8 (RBAC/audit), 16 (Stack) · **Status:** Build
· **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: config-as-data (CC-4), multi-tenant (CC-1), credential security
(CC-10/CC-12), traceability (CC-3), audit (CC-5/audit).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §4.2.

## Objective

Make **anything the user creates copyable**: one consistent "Duplicate" action
across every reusable entity, so a proven setup can be reused as the starting
point for a new one — within a tenant or, for admins, into another tenant.

## Scope

- **In:** clone for `MappingConfig`, `RuleSet` (+ child `Rule`s), `FeedTemplate`,
  `ConnectorConfig` (config only), `Stack`, and a whole **customer/workspace**
  config setup; a `cloned_from` provenance pointer; audit on every clone; a
  Duplicate affordance + dialog in the UI.
- **Out:** cloning **secrets/credentials** (never — CC-10/CC-12), sessions, audit
  records, or `output_row`/`StackRow` data (a clone starts empty and re-runs);
  live "fork and keep in sync" (a clone is an independent copy, not a link).

## Cross-cutting

- **CC-4** clones are new versioned config rows (`version=1`, `lifecycle_status=
  "draft"`), never code.
- **CC-1** clone writes are tenant-scoped; **cross-tenant clone is an explicit
  `admin` action** that reads the source (tenant-checked) and writes into the
  target tenant only.
- **CC-10/CC-12** a `ConnectorConfig` clone copies non-secret settings only; the
  `ConnectorCredential` / `secret_ref` is **never** copied — the clone starts
  unauthenticated.
- **CC-3** every clone records `cloned_from` (source id + version) for provenance.
- **audit** every clone writes an `audit_log` entry (actor, action `clone`, target).

## Functional Requirements

- **P15-1 Clone semantics:** deep-copy the entity (and its children, e.g. a rule
  set's rules) into new rows with a fresh UUID, `version=1`,
  `lifecycle_status="draft"`, `created_by=<actor>`, and `cloned_from=<source>`. The
  clone is fully independent thereafter.
- **P15-2 Entity coverage:** a small `clone` service per entity family (leaning on
  `services/config_versioning.py`) + `POST …/{id}/clone` endpoints on the relevant
  routers (`configs`, `feed_templates`, `connectors`, `stacks`, `customers`).
- **P15-3 Workspace/customer clone:** bulk-clone a customer's config setup
  (mapping configs, rule sets, feed templates, connector configs **sans
  credentials**, tenant settings) into a **new or existing** target customer —
  an admin action, tenant-boundary enforced, fully audited.
- **P15-4 Provenance:** add a nullable `cloned_from` column to the cloneable
  entities; surface "cloned from X" in the UI.
- **P15-5 UI:** a "Duplicate" item in row action menus on `app/configs`,
  `app/feeds`, `app/sources`, `app/customers`, and the Stack browser; a clone
  dialog (reuse `components/ui/dialog.tsx`) with a new name and, for admins, a
  target-customer picker (`components/ui/searchable-select.tsx`).

## Deliverables

- `cloned_from` columns + migration on cloneable entities.
- Clone service(s) + `POST …/{id}/clone` endpoints (RBAC: `write_config`;
  cross-tenant = `admin`); audit entries.
- UI Duplicate affordance + dialog across the listed screens.
- Tests: deep-copy correctness (children copied, new ids, draft status), **secrets
  never copied**, cross-tenant clone respects boundaries + audit, provenance set.

## Acceptance Criteria

- Duplicating a rule set produces an independent draft copy with all rules,
  `cloned_from` set, and an audit entry; editing the copy never affects the source.
- Duplicating a connector config copies settings but **not** the credential — the
  clone is unauthenticated until a new credential is attached.
- An admin clones customer A's whole setup into customer B: B gains the configs
  (as drafts) and **no** secrets; every create is audited and tenant-scoped.
- A non-admin cannot clone across tenants (403); a viewer cannot clone (403).
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phases 2, 3, 8; Phase 16 for Stack clone (build Stack clone after 16 lands).

## Open Questions

- **OQ-15.1** naming collisions on clone — auto-suffix ("… (copy)") vs require a
  new name. Default: pre-fill "… (copy)", editable.
- **OQ-15.2** existing-target customer clone — merge vs skip on name/signature
  collisions. Default: create new versions as drafts; never overwrite published.

## Sub-phases

TBD — likely a per-entity-clone slice and a customer/workspace-clone slice at
build time (per the sub-phase convention in [`README.md`](./README.md)).
