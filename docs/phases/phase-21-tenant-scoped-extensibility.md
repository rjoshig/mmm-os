# Phase 21 — Tenant-Scoped Extensibility & Flexibility

**Depends on:** 0 (canonical schema), 2 (mapping), 3 (custom-rule DSL), 4 (checks), 6 (UI)
· **Status:** Build · **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: multi-tenant (CC-1), config-as-data (CC-4), portability (SQLite→Postgres),
human-in-the-loop (CC-5).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §6.

## Objective

Let a customer **extend the platform without code** — add their own dimensions,
measures, factors, layouts, and validation checks, scoped to their workspace — via
versioned, metadata-driven config that the UI and engines render automatically.

## Scope

- **In:** a `schema_extension` metadata registry (custom dimensions/measures/
  factors per tenant); resolved-schema plumbing so extensions appear everywhere;
  per-tenant saved layouts/views; expression-based custom checks; a metadata-driven
  Admin UI to manage all of it.
- **Out:** altering the **core** canonical contract per tenant (core stays fixed);
  EAV / schema-per-tenant approaches (rejected — see ADR-015); a full external
  semantic-layer product (documented as north-star direction only).

## Cross-cutting

- **CC-1** every extension row, layout, and custom check is `tenant_id`-scoped.
- **CC-4** extensions are versioned config data (layered global → template →
  customer), never code.
- **Portability** extension **values** live in the existing JSON columns
  (`OutputRow.data` / `StackRow`), so no per-tenant migrations; the registry uses
  dialect-agnostic types (SQLite→Postgres, ADR-002).
- **CC-5** custom checks run within the sandboxed DSL (ADR-004) — no arbitrary code.

## Functional Requirements

- **P21-1 `schema_extension` registry** — a versioned config entity: `tenant_id`,
  `kind` (dimension | measure | factor), `name`, `data_type`, `taxonomy_ref`,
  `validation`, `layer`, `version`, `lifecycle_status`. The canonical **core**
  stays the fixed contract; extensions add on top (ADR-015).
- **P21-2 Resolved schema** — a resolver returns **core + tenant extensions**; the
  UI and engines read the resolved schema so custom fields auto-appear as mapping
  targets (`mapping/engine.py`, `canonical/loader.py`), transform targets,
  validation subjects, stack columns, and export-contract columns. Extension values
  are JSON keys — **no migration** to add a field.
- **P21-3 Custom layouts / views** — per-tenant saved column layouts, ordering, and
  view presets for tables/mapping/stack browser (extend `data-table.tsx`). Output/
  stack layouts complement the existing input `FeedTemplate`.
- **P21-4 Custom checks** — expression-based validation checks as config-as-data via
  the sandboxed DSL (ADR-004, `transform/operations_custom.py`) — a tenant writes
  `clicks <= impressions`-style rules safely, scoped to their workspace (feeds
  Phase 17's registry).
- **P21-5 Metadata-driven UI** — components render fields from the resolved schema
  (not hardcoded lists); an Admin → "Schema & Fields" panel to define custom
  dimensions/measures/factors, taxonomies, layouts, and checks; all versioned,
  draft→publish, audited.

## Deliverables

- `schema_extension` model + migration (tenant-scoped, dialect-agnostic) + a
  resolved-schema service.
- Engine/UI wiring to read the resolved schema (mapping/transform/validation/stack/
  export contract).
- Per-tenant layouts/views storage + UI; custom-check config (into Phase-17 registry).
- Admin "Schema & Fields" UI.
- Tests: a custom dimension appears as a mapping target and lands in output/stack
  JSON with **no** migration; extensions are tenant-isolated; a custom check fires;
  portability (SQLite + Postgres) holds.

## Acceptance Criteria

- Defining a custom dimension for tenant A makes it a selectable mapping target and
  a stack column for A only; it does **not** appear for tenant B (CC-1).
- The custom field's values persist in the existing JSON column with **no schema
  migration**.
- A tenant-authored custom check (`clicks <= impressions`) runs within the sandbox
  and produces flags; it cannot execute arbitrary code (ADR-004).
- A saved layout/view persists per tenant and restores on return.
- Backend `ruff`/`mypy`/`pytest` (incl. Postgres-portability) and front-end
  `typecheck`/`lint`/`build` pass.

## Dependencies

Phase 0 (canonical schema + loader), Phase 2 (mapping), Phase 3 (sandboxed DSL),
Phase 4 (check registry), Phase 6 (UI). Read by Phase 16 (stack columns) and
Phase 17 (custom checks).

## Open Questions

- **OQ-21.1** extension storage — JSON columns + metadata registry (recommended) vs
  EAV vs per-tenant schema. Default: JSON + registry (ADR-015).
- **OQ-21.2** do custom dimensions participate in anomaly slicing / required-field
  gates, or advisory only by default? Default: advisory unless marked required.
- **OQ-21.3** custom-check safety — bound the DSL (no unbounded cross-row/global
  scans) and cap checks per tenant.
- **OQ-21.4** how far to formalize the semantic-layer / headless-BI framing now
  (export-contract API as the governed interface) vs later.

## Sub-phases

TBD — likely a registry/resolved-schema slice and a layouts/custom-checks slice at
build time (per the sub-phase convention in [`README.md`](./README.md)).
