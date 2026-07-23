# Phase 3 — Transformation Rule Engine

**Depends on:** Phases 0, 2 · **Status:** Done (all sub-phases implemented; pending PR merge) · **MVP:** yes (Phases 0–4)

Cross-cutting: config-as-data (CC-4), idempotent jobs (CC-6), traceability (CC-3).

## Objective

Apply declarative, config-driven transformations that clean and standardise
mapped data, with live before/after preview.

## Scope

- **In:** declarative rule schema; operation library; ordered rule application;
  layered rules; preview.
- **Out:** validation/anomaly (Phase 4), AI suggestions (Phase 5), UI (Phase 6).

## Functional Requirements

- **P3-1 Rule schema:** each rule stored as data: `{ id, target_field, operation, params, condition, order }`. *(See [`../data-model.md`](../data-model.md), Appendix D.)*
- **P3-2 Operation library (v1):** MUST include `map_value`, `rename_column`, `cast_type`, `parse_date`, `convert_currency`, `dedupe`, `reshape` (wide→long), `fill_missing`, `trim/normalize_text`, `custom`. MUST be **extensible** (new operation = new handler, no rewrite).
- **P3-2b Time-grain `aggregate` (Cycle 2):** roll a table up to a coarser date grain (weekly/monthly) — measures summed, numeric factors averaged, dimensions preserved as grouping keys, date series gap-filled to be continuous. Schema-aware (auto-classifies via the canonical schema in `RuleContext`) with explicit `group_by`/`sum`/`mean` overrides. Resolves the canonical-schema A.4 granularity decision (weekly = MMM-standard grain).
- **P3-2c Reporting normalization (Cycle 2):** `convert_currency` gains a **to-reporting** mode — normalize each row's value from its source currency into the tenant **reporting currency** using the per-tenant FX table; and a new **`normalize_timezone`** op converts a timestamp to the tenant **reporting timezone** (optionally deriving the reporting-frame date). Both read the reporting frame from `RuleContext.reporting` (per-tenant `tenant_settings`). This makes currency + timezone normalization consistent tenant-wide.
- **P3-3 Escape hatch:** provide a `custom` rule type for the ~10% of cases the library doesn't cover. *(Scope of this is OQ-3.1.)*
- **P3-4 Ordered application:** rules apply in defined order; deterministic output.
- **P3-5 Layered rules:** global defaults → template rules → customer overrides, merged at runtime.
- **P3-6 Taxonomy harmonisation:** `map_value` MUST support collapsing raw values to canonical taxonomy terms (e.g. `FB`, `fb_ads` → `Facebook`).
- **P3-7 Preview:** given a rule (or rule set) + sample rows, return **before/after** without persisting — this powers the UI later.
- **P3-8 Versioning:** rule sets versioned; outputs traceable to the rule-set version applied.

## Deliverables

- Rule engine (declarative, ordered, layered).
- v1 operation handlers + `custom` escape hatch.
- Preview service (before/after on sample rows).
- Versioned `rule_set` storage.

## Acceptance Criteria

- Define a `map_value` rule collapsing 3 raw channel spellings to one canonical value → applied output shows the single canonical value.
- Define `parse_date` + `convert_currency` + `dedupe` → output reflects all three in order, deterministically.
- Preview endpoint returns correct before/after for a rule set on sample rows without writing anything.
- Re-running with the same rule-set version yields identical output (idempotent).

## Dependencies

Phases 0, 2.

## Open Questions

- **OQ-3.1** — ✅ Resolved: `custom` = a **sandboxed expression language** (restricted DSL over the row/field context; no arbitrary code, imports, or I/O; allowlisted ops; resource-bounded). The evaluator is security-critical — strict allowlist + hard resource limits + adversarial tests. Grammar/function set finalised in this phase. See ADR-004.
- **OQ-3.2** — ✅ Resolved (draft): reshape config model `{ id_vars, value_vars | value_var_pattern, var_name → dimension, value_name → measure }`; deterministic. Edge cases refined during implementation.

**Operation-library open items (future, connector-driven).** Each is a **new
operation handler** added when Phase 9 is scoped (no rewrite — new handler only,
per P3-2). Driven by the partner mapping templates (Phase 09.7); see the connector
docs under [`../connectors/`](../connectors/):
- **`extract_action`** (Meta) — pull a measure for a chosen `action_type` from a
  nested array (`actions` / `action_values`, keyed e.g. by `purchase`/`lead`); the
  chosen `action_type` is a per-tenant config value.
- **`micros_to_currency`** (Google Ads) — divide `cost_micros` by 1,000,000 to get
  account-currency spend.
- **`resolve_geo_target`** (Google Ads) — resolve a geo-target-constant **ID**
  (`country_criterion_id`) to a country before taxonomy mapping.
- **`flatten_report_row`** (TikTok) — merge the split `dimensions` / `metrics`
  objects of a report row into one flat row before mapping.
- **string→number `cast_type`** (TikTok) — numeric metrics arrive as strings and
  must be cast (an extension of the existing `cast_type` op).
- **`strip_report_totals`** (DV360) — drop the trailing grand-total / summary rows
  of a Bid Manager offline CSV report before mapping.

_All Phase-3 MVP open questions resolved; the operation-library items above are
deferred connector-era extensions. See [`../open-questions.md`](../open-questions.md)._

## Sub-phases

Phase 3 is implemented as two PR-sized sub-phases (one per branch/PR):

- [`phase-03.1-rule-engine-core.md`](./phase-03.1-rule-engine-core.md) — rule schema, ordered/layered engine, operation registry, structural ops (P3-1, P3-4, P3-5). **Done.**
- [`phase-03.2-value-ops-preview-api.md`](./phase-03.2-value-ops-preview-api.md) — value/taxonomy ops, sandboxed `custom` op, preview, versioned rule-set persistence + API (P3-2, P3-3, P3-6, P3-7, P3-8). **Done.**
