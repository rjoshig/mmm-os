# Phase 06.4 — Transformation Builder + Live Preview

**Parent:** [`phase-06`](./phase-06-review-ui-nextjs.md) · **Depends on:** 06.1,
06.3 · **Status:** Done (Cycle-1 UX overhaul: full operation set + signature-scoped
rule-set reuse). Covers **P6-3**, **P6-4**.

## Objective

Let a user author transformation rules by UI actions (pick a column → choose an
operation → configure) with an immediate before/after preview — never exposing raw
JSON.

## Scope

- **In:** action-based rule builder (operation picker + per-op config forms, e.g.
  collapse distinct raw values to a canonical term); an ordered rule list; live
  before/after preview on sample rows; save rule set.
- **Out:** validation (06.5).

## Functional Requirements

- **P6.4-1** Add a rule by selecting a column + operation and configuring it via
  form controls (no JSON). Each action authors one `RuleSpec`.
- **P6.4-2** Show the ordered rule list; allow reorder/remove.
- **P6.4-3** Live before/after preview via the `/transform/preview` endpoint on
  sample rows, updating on every change (P6-4).
- **P6.4-4** Save the rule set (versioned). Rule sets are keyed by the sheet's
  **column signature** (not `sheet_id`), so a rule set saved on one sheet is reused
  by any file with identical headers ("configure once, reuse forever" — mirrors
  mapping configs). Persisted via `GET`/`POST /sheets/{sheet_id}/rule-set`, which
  derive the signature-scoped name server-side.
- **P6.4-5** Expose the **full operation set** (all registered operations):
  `normalize_text`, `map_value`, `fill_missing`, `rename_column`, `cast_type`,
  `parse_date`, `convert_currency`, `dedupe`, `reshape`, `custom`, and `aggregate`
  (Cycle 2 — weekly/monthly grain) — each with a typed config form (no JSON).

## Deliverables

- Transformation-builder route + components (op picker, config forms incl.
  currency/dedupe/reshape/custom, preview table).
- Signature-scoped rule-set endpoints + `transform.service` signature helpers
  (`rule_set_name_for_sheet`, `get_rule_set_for_sheet`); output/validation/
  pipeline-status all resolve rules by signature.

## Acceptance Criteria

- A user collapses messy channel values via the UI and sees live before/after;
  saving persists a versioned rule set; no JSON shown.
- A rule set saved on one sheet is found by a **different** sheet with identical
  headers (covered by `test_rule_set_reused_across_sheets_of_same_signature`).
- All 10 operations are selectable with typed config forms.
- `typecheck`/`lint`/`build` pass; backend `ruff`/`mypy`/`pytest` pass.

## Dependencies

06.1/06.3; Phase 3 transform preview + rule-set APIs.

## Open Questions

None.

## Sub-phases

N/A (leaf).
