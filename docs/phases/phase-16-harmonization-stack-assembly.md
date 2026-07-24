# Phase 16 — Stage 2: Harmonization & Stack Assembly (Gold Layer)

**Depends on:** 2 (mapping), 3 (transform/aggregate), 4 (validation), 5 (AI), 6 (UI),
14 (destinations), 17 (panel validation), 21 (resolved schema)
· **Status:** Build · **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: traceability (CC-3), config-as-data (CC-4), human-in-the-loop (CC-5),
idempotent (CC-6), LLM budget (CC-13), semantic integrity (CC-15).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §2, §3, §4.3.

## Objective

Add the **second stage** of the pipeline — a dedicated surface where cleaned
(**Silver**) per-source output is pulled in and finished into a **model-ready
Stack (Gold)**: unified across sources (taxonomy, currency/timezone/attribution,
grain), semantically mapped, panel-validated, and published as a named, versioned
dataset ready for MMM modelling.

## Why now (the gap)

Today the model-ready dataset exists only implicitly as `output_row` rows for one
job, and there is no step that **harmonizes multiple sources** into one panel.
Reaching a modelling-ready state is a distinct activity from per-source cleaning —
periodic, cross-source, and deliberate — so it deserves its own surface (the
medallion **Gold** layer). See ADR-014 for the two-stage decision and ADR-012 for
Stack-as-entity.

## Scope

- **In:** the `Stack` / `StackRow` entities; assembly of one or more Silver outputs
  into one panel; a config-as-data harmonization engine (taxonomy/value
  harmonization, semantic field mapping, currency/timezone/attribution
  reconciliation, entity resolution); AI-assisted harmonization suggestions; a
  Harmonize/Stacks UI surface; Stack publish (gated by panel validation) + export
  contract + destination export + lineage.
- **Out:** the MMM model itself (always out of scope); real-time streaming
  assembly; warehouse push beyond the Phase-14 destination abstraction.

## Cross-cutting

- **CC-3** a Stack traces **Gold → Silver outputs → Bronze files** (full lineage).
- **CC-4** harmonization rules and the semantic map are versioned config data,
  layered global → template → customer.
- **CC-5** AI harmonization only **suggests**; a human accepts/rejects/modifies.
- **CC-6** publishing a Stack is idempotent — re-publishing the same inputs +
  config yields the same panel, no duplicate rows.
- **CC-13** AI harmonization is metered by the existing per-tenant LLM budget.
- **CC-15** panel (cross-source) validation runs and gates publish.

## Functional Requirements

Grouped by sub-phase (see **Sub-phases**).

- **P16-1 Stack entity + assembly (16.1):** `Stack` (name, description, `version`,
  `lifecycle_status` draft|published|archived, `tenant_id`, `grain`, reporting
  frame, schema-contract snapshot, `created_by`, `cloned_from`) and `StackRow`
  (canonical row linked via `stack_id` / `stack_version`, keeping the existing
  traceability columns). A Stack **assembles one or more Silver outputs** (files /
  sources / sync runs) into one panel, reconciling grain via the existing
  `transform/operations_aggregate.py` and reporting frame via `tenant_settings`.
- **P16-2 Harmonization engine (16.2):** a versioned harmonization rule set + a
  semantic map that unify **across sources** — taxonomy/value harmonization
  (reusing `Taxonomy`/`TaxonomyAlias`), semantic field mapping (source
  `link_clicks` → canonical `clicks`), currency/timezone/attribution-window
  reconciliation to the reporting frame, and entity resolution
  (attribute-align → block → link → canonicalize) for campaign/geo/product naming.
- **P16-3 AI-assisted harmonization (16.3):** new suggestion kinds in
  `src/mmm_os/ai/` — draft taxonomy/value harmonization, semantic field matches,
  and entity-resolution proposals — each with confidence + rationale, ratified by
  a human (CC-5), metered by CC-13.
- **P16-4 Publish + gate:** publishing materializes a named Stack version, gated on
  panel (Gold) validation passing (Phase 17); idempotent (CC-6); a Stack requires
  the appropriate permission (Phase 19).
- **P16-5 Export + lineage:** the existing export contract
  (`GET /jobs/{id}/output/contract`) becomes the **Stack contract**; CSV +
  destination export (Phase 14) attach to the Stack; the lineage panel points at
  the Stack (Gold → Silver → Bronze).
- **P16-6 UI — the second surface:** a new top-level **Harmonize / Stacks** sidebar
  section: pick Silver sources → harmonization builder (semantic map + AI assist,
  live before/after preview reusing `CompactPreview`) → panel validation + output
  stats → publish → browse/clone/export versions + view lineage. Its own **Stage-2
  dashboard** (stacks published, harmonization coverage, panel data-quality),
  distinct from the Stage-1 per-file dashboard.

## Deliverables

- `Stack` + `StackRow` models + migrations (tenant-scoped, dialect-agnostic).
- Assembly service; harmonization engine (config-as-data) + semantic map;
  AI suggestion kinds; publish/gate; export contract + destination export; lineage.
- Backend endpoints (thin routers, tenant + RBAC enforced).
- Review-UI **Harmonize / Stacks** surface + Stage-2 dashboard.
- Docs kept in sync (this spec + sub-phase specs, README status, build-plan,
  data-model entities, canonical-schema cross-ref).

## Acceptance Criteria

- Two Silver outputs from different sources (e.g. Meta + Google), with divergent
  channel naming and currencies, assemble into **one** weekly panel with a single
  canonical taxonomy and one reporting currency.
- Publishing produces a named, versioned Stack; re-publishing the same inputs +
  config produces an identical panel (no duplicate rows) — CC-6.
- The Stack traces every row back through its Silver output to the Bronze file
  (CC-3); the export contract lists canonical + tenant-extension columns with
  types, row count, and applied config versions.
- Panel validation failures **block** publish until resolved/overridden (CC-15).
- AI harmonization suggestions are advisory only; nothing commits without human
  acceptance (CC-5); usage is metered (CC-13).
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phases 2, 3, 4, 5, 6; Phase 14 (destinations), Phase 17 (panel validation),
Phase 21 (resolved schema incl. tenant extensions), Phase 19 (publish permission).

## Open Questions

- **OQ-16.1** Stack scope — a Stack aggregates multiple Silver outputs (confirmed);
  max sources per stack; incremental append vs full rebuild on re-publish?
- **OQ-16.2** harmonization rules vs Stage-1 rule sets — a separate config family
  (recommended) vs reusing `RuleSet` with a scope flag?
- **OQ-16.3** AI harmonization — deterministic alias table first, LLM only for the
  residual; auto-suggest vs require-review confidence threshold.

## Sub-phases

Built in order; each a PR-sized slice with its own spec:

- [`phase-16.1-stack-entity-assembly.md`](./phase-16.1-stack-entity-assembly.md) — Stack/StackRow entities + assembly of Silver outputs (P16-1, P16-4, P16-5).
- [`phase-16.2-semantic-mapping-harmonization.md`](./phase-16.2-semantic-mapping-harmonization.md) — harmonization engine + semantic map + entity resolution (P16-2).
- [`phase-16.3-ai-assisted-harmonization.md`](./phase-16.3-ai-assisted-harmonization.md) — AI-assisted harmonization suggestions (P16-3).
