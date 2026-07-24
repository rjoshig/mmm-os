# Phase 16.1 — Stack Entity & Assembly

**Parent:** [`phase-16-harmonization-stack-assembly.md`](./phase-16-harmonization-stack-assembly.md)
· **Status:** Build · **Cycle:** 5

Cross-cutting: traceability (CC-3), config-as-data (CC-4), idempotent (CC-6).

## Objective

Introduce the first-class **`Stack`** (Gold, model-ready dataset) and assemble one
or more Silver outputs into a single canonical panel that can be published,
browsed, exported, and cloned.

## Functional Requirements

- **P16.1-1** `Stack` model (name, description, `version`, `lifecycle_status`
  draft|published|archived, `tenant_id`, `grain`, reporting-frame snapshot,
  schema-contract snapshot, `created_by`, `cloned_from`) — tenant-scoped,
  dialect-agnostic types.
- **P16.1-2** `StackRow` model — the canonical row linked to a stack via
  `stack_id` / `stack_version`, retaining the traceability columns
  (`source_file_id`, `source_sheet`, `source_row`, applied config versions,
  `ingested_at`) so lineage reaches Bronze (CC-3). Reuse the `OutputRow` shape;
  `StackRow` may be `OutputRow` with a `stack_id` FK rather than a new table
  (decide at build).
- **P16.1-3** Assembly service — take a set of Silver outputs (jobs / sync runs /
  files), align grain via `transform/operations_aggregate.py`, apply the reporting
  frame from `tenant_settings`, and produce the panel. Idempotent (CC-6).
- **P16.1-4** Publish — materialize a named Stack version; gated on panel
  validation (Phase 17). Re-publish replaces, never duplicates.
- **P16.1-5** Export contract + destination export — the export contract becomes
  the Stack's; CSV + Phase-14 destination export attach to the Stack; lineage
  endpoint returns Gold → Silver → Bronze.

## Acceptance Criteria

- Assembling two Silver outputs yields one panel with combined rows on a common
  grid; publishing creates version 1; re-publishing yields an identical version
  (no dup rows).
- The Stack's export contract lists canonical + tenant-extension columns with
  types + applied config versions; lineage resolves to Bronze files.
- Backend `ruff`/`mypy`/`pytest` pass; front-end (Stacks browser stub) builds.

## Dependencies

Phase 3 (aggregate op), Phase 14 (destination), Phase 17 (validation gate).

## Open Questions

Inherits parent OQ-16.1. Additional: is `StackRow` a new table or `OutputRow +
stack_id`? Default: reuse `OutputRow` with a nullable `stack_id`/`stack_version`.
