# Phase 17 — Semantic & Output Validation + Failure Visualization

**Depends on:** 4 (validation engine), 6 (UI), 16 (Stack, for panel checks)
· **Status:** Build · **Cycle:** 5 (Usability, Reuse & Model-Readiness)

Cross-cutting: **CC-15 semantic integrity** (new), human-in-the-loop (CC-5),
observability (CC-7), config-as-data (CC-4).

See the umbrella design: [`../design/usability-reuse-model-readiness.md`](../design/usability-reuse-model-readiness.md) §5.

## Objective

Move validation beyond structural checks to **meaningful (semantic) validation** —
checks that catch data errors by making sense of the data (e.g. `clicks ≤
impressions`) — add **output statistics** (min/max/mean/…), and **visualize
failures**, at both the per-source (Silver) and cross-source panel (Gold) layers.

## Scope

- **In:** a semantic (cross-field) check family; cross-source panel checks;
  per-measure output statistics; failure visualization in the review UI; config-as-
  data severity + tenant-extensible custom checks (hook to Phase 21).
- **Out:** MMM *model*-level QA (baseline reconciliation, ROI plausibility, adstock
  realism — those belong to the modelling engine, out of scope); per-flag AI
  remediation (Cycle 4).

## Cross-cutting

- **CC-15** cross-field and cross-source semantic checks run and **gate** Stack
  publish.
- **CC-4** checks + severity are config data; custom checks are tenant config
  (Phase 21).
- **CC-5** semantic flags follow the same acknowledge/resolve/override review
  lifecycle as Phase 4.
- **CC-7** validation runs emit status/timing on the job timeline.

## Functional Requirements

- **P17-1 Semantic (cross-field) checks** — a new declarative check family in
  `validation/checks.py` (extend the registry + `policy.py`), covering the catalog
  below. Config-as-data severity; grain-aware where relevant.
- **P17-2 Check catalog (by data-quality dimension):**
  - **Completeness** — required fields present; per-field null-rate thresholds;
    date-grid completeness (no missing periods at grain); expected-channel coverage.
  - **Uniqueness** — duplicate rows *(exists)*; duplicate `(date × dimensions)` key;
    duplicate campaign across sources.
  - **Consistency (semantic)** — funnel monotonicity (`clicks ≤ impressions`,
    `conversions ≤ clicks`, `reach ≤ impressions`); CTR in band; CVR in band;
    CPC/CPM sanity; spend↔delivery coherence (`spend > 0 ⇒ impressions > 0`);
    revenue↔conversion coherence.
  - **Validity** — value ∈ canonical taxonomy; type/format; range (measures ≥ 0;
    date within reporting window); ISO-4217 currency code.
  - **Timeliness/continuity** — grain-aware continuity *(exists)*; freshness;
    week-over-week spike/drop.
  - **Accuracy/reasonableness** — z-score/IQR outliers *(exists)*; zero/near-constant
    series; unit & magnitude sanity; mixed-currency detection (pre-harmonization).
  - **Cross-source (Gold/panel)** — total-spend reconciliation across sources within
    ±X%; taxonomy completeness; duplicate-source overlap; attribution-window
    consistency; currency/timezone alignment.
- **P17-3 Output statistics** — per measure: min / max / mean / median / stddev /
  null-rate / row-count, plus week-over-week deltas, computed on the Stack and
  shown before publish (extends `validation/anomaly.py`).
- **P17-4 Layered gate** — Silver checks run in Stage 1; panel (Gold) checks run
  before a Stack can publish (CC-15).
- **P17-5 Failure visualization** — the validation review UI
  (`app/files/[fileId]/validation/page.tsx`, `components/validation/flag-clusters.tsx`)
  gains a distribution/spark view of failing rows per check + a stats table. This
  is the first charting need — make an explicit bespoke-SVG-vs-library decision
  under the design system (OQ-17.2).

## Deliverables

- Semantic check family + cross-source panel checks (config-as-data severity).
- Output-statistics profiler surfaced on the Stack.
- Validation-UI failure visualization + stats table.
- Tests: each semantic check fires on a crafted violation and passes clean data;
  panel checks gate Stack publish; output stats computed correctly.

## Acceptance Criteria

- A row with `clicks > impressions` produces a semantic flag; a row with implausible
  CTR is flagged per policy; clean data produces none.
- A panel whose per-source spend fails cross-source reconciliation (>±X%) **blocks**
  Stack publish until resolved/overridden (CC-15).
- The Stack shows per-measure min/max/mean/median/stddev/null-rate/row-count before
  publish.
- The validation screen visualizes failing-row distribution per check.
- Backend `ruff`/`mypy`/`pytest` and front-end `typecheck`/`lint`/`build` pass.

## Dependencies

Phase 4 (engine + review lifecycle), Phase 6 (UI); Phase 16 for panel checks +
Stack stats; Phase 21 for tenant-extensible custom checks.

## Open Questions

- **OQ-17.1** CTR/CPC/CPM plausibility bounds — default bands + per-tenant override.
- **OQ-17.2** charting — bespoke SVG vs the first charting dependency (respect
  [`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md)).

## Sub-phases

TBD — likely a semantic-check-engine slice and a failure-visualization/stats slice
at build time (per the sub-phase convention in [`README.md`](./README.md)).
