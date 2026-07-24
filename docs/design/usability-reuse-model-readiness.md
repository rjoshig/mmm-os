# Design — Usability, Reuse & Model-Readiness (Cycle 5)

**Status:** Design v0.1 — documentation only (no implementation in this doc).
**Companion to:** [`../prd.md`](../prd.md), [`../build-plan.md`](../build-plan.md),
[`../architecture.md`](../architecture.md), [`../canonical-schema.md`](../canonical-schema.md),
[`../phases/README.md`](../phases/README.md).
**Scope of this doc:** the master design for a new work track — **Cycle 5** — that
makes the platform more usable, more reusable, and able to reach a **model-ready
"stack"**. It defines eight workstreams, specified as phases **14–21** in
[`../phases/`](../phases/).

> This is the "doc we can work on." It is intentionally a design/rationale
> document; each workstream has a matching phase spec with Objective · Scope ·
> Functional Requirements · Deliverables · Acceptance Criteria · Dependencies ·
> Open Questions. Nothing here is built yet — it is the plan of record for the
> next cycle, to be implemented one phase per PR (per [`../../GIT_STANDARDS.md`](../../GIT_STANDARDS.md)).

---

## 1. Motivation

`mmm-os` already implements a full, multi-tenant ingest → map → transform →
validate → output pipeline with a real Review UI, connectors, RBAC, and
governance (phases 0–13, all Done). This cycle addresses the gaps that make the
platform *pleasant, reusable, and genuinely model-ready* rather than just
functional:

- **Monitor pipeline runs live** — the runs view exists but doesn't refresh while
  a job is in flight.
- **Clone / duplicate anything** — no way to copy a config, mapping, rule set,
  feed template, connector, stack, or a whole customer's setup. Every reuse today
  is implicit (column-signature auto-match) or manual.
- **Config-driven I/O** — output is a DB table + browser CSV download only; there
  is no root configuration of input/output/temp/archive/error/reject paths, and
  no push of output to a configured destination.
- **Meaningful (semantic) validation** — checks are structural (missing fields,
  negatives, gaps, statistical outliers). There is no cross-field business-rule
  validation (e.g. `clicks ≤ impressions`), no output-level statistics
  (min/max/mean), and thin failure visualization.
- **A first-class "stack"** — the model-ready dataset exists only implicitly as
  `output_row` rows for one job; it is not a named, versioned, publishable
  artifact, and there is no cross-source harmonization step to build one.
- **A test environment** — no safe, in-app space to try configs before publishing.
- **A better dashboard** — the dashboard is per-file operational; there is no
  tenant-level KPI/analytics rollup.
- **Improved RBAC** — three roles (admin/member/viewer), no distinct approver or
  platform-admin, no role-management UI.
- **Per-customer flexibility** — the canonical schema is a fixed contract; there
  is no way for a customer to add their own dimensions/measures/factors, layouts,
  or checks without code.

---

## 2. Organizing principle — a two-stage medallion (Bronze → Silver → Gold)

The most important design decision in this cycle is **how we reach a
modelling-ready state**. The answer is a **two-stage pipeline** on the
industry-standard **medallion architecture**, which cleanly separates *cleaning a
single source* from *harmonizing many sources into one modelling panel*.

| Layer | What it is | In `mmm-os` | Status |
|---|---|---|---|
| **Bronze — raw** | Immutable source files exactly as they arrived | `File` + `ObjectStorage` (CC-2) | Exists |
| **Silver — cleaned, per-source** | One source, mapped to canonical schema, transformed, validated | Today's pipeline → `output_row` | Exists — **Stage 1 "Prepare"** |
| **Gold — harmonized, model-ready** | Many Silver outputs unified into one panel: cross-source taxonomy, currency/timezone/attribution reconciliation, grain alignment, semantic mapping, panel validation | New `Stack` entity | **New — Stage 2 "Harmonize & Assemble"** |

**Stage 1 — Prepare (Silver).** Unchanged. A user ingests, maps, transforms, and
validates one file/source at a time. This is frequent and file-by-file.

**Stage 2 — Harmonize & Assemble (Gold).** A **new second surface** (its own
sidebar area). A user pulls in one or more *prepared* (Silver) outputs and
finishes them into a model-ready **Stack**:
- **Taxonomy harmonization** across sources (Meta "FB" / Google "Facebook" →
  canonical `meta`), reusing `Taxonomy`/`TaxonomyAlias`.
- **Semantic field mapping** across sources (source `link_clicks` → canonical
  `clicks`) — distinct from Stage-1 per-source column mapping.
- **Reconciliation** of currency, timezone, and attribution window to a common
  reporting frame (`tenant_settings`).
- **Grain alignment** (daily → weekly, the MMM-standard target) via the existing
  `aggregate` op.
- **Entity resolution** for campaign/geo/product naming.
- **Panel validation** (semantic + output statistics) as the publish gate.
- **Publish** a named, versioned Stack.

### Why two stages beats one long pipeline

- **Cadence & mental model** — per-source cleaning is frequent and mechanical;
  harmonization is periodic, cross-source, and deliberate. Different jobs, done at
  different times, by (often) different people.
- **Reuse** — one cleaned Silver source feeds *many* Stacks without re-cleaning.
- **Governance** — the Stack (Gold) is the single certified, approved,
  lineage-traced hand-off to modelling, with its own validation gate + export
  contract + approval (RBAC, Phase 19).
- **AI scoping** — AI-assisted *harmonization* (taxonomy/entity resolution across
  sources) has a natural home in Stage 2, distinct from the per-source
  column-mapping AI already in Stage 1 (`src/mmm_os/ai/`).
- **UX** — two focused surfaces beat one overloaded pipeline.

### The guardrail — a surface, not a silo

The two stages **share** one canonical schema, config-as-data (CC-4), end-to-end
lineage (a Stack traces Gold → Silver outputs → Bronze files, CC-3), and one
design system ([`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md)). Stage 2
is a *surface*, not a separate product. See **ADR-014**.

---

## 3. What "a stack" is (the DataOS centerpiece)

Mutinex DataOS is the *data provisioning* layer that feeds MMM modelling
(GrowthOS); `mmm-os` plays the same role and is **not** the model itself. In that
world a **stack** is the *finished, model-ready dataset* handed to modelling — a
clean, canonical, validated **panel**: a long/tidy table on a time grid of

- **dimensions** — `date`, `channel`, `sub_channel`, `campaign`, `ad_group`,
  `geo`, `product`, `funnel_stage`
- **measures** — `spend`, `impressions`, `clicks`, `conversions`, `revenue`,
  `reach`
- **factors / external regressors** — `seasonality_index`, `is_holiday`,
  `price_index`, `on_promotion`, `distribution`, `competitor_spend`, …

(the fields defined in [`../canonical-schema.md`](../canonical-schema.md)).

Today this is implicit: `output_row` rows for a single job. This cycle makes
**`Stack`** a first-class entity (**ADR-012**): a *named, versioned, published*
model-ready dataset with a schema contract, output-validation statistics,
lineage, clone, and destination export. It is the **Gold** layer of §2, and the
artifact a modeler consumes via the export contract. A Stack **assembles one or
more Silver outputs** into one panel — it is not a rename of one job's output.

---

## 4. The eight workstreams (phases 14–21)

Each is specified in its own phase file; this section is the design rationale and
the map to those specs.

| Phase | Workstream | Answers the ask |
|---|---|---|
| 14 | Config-driven I/O paths & destinations | root config for input/output/temp/archive/error/reject; write output to a configured path |
| 15 | Universal clone / duplicate | copy any config/mapping/rule/template/connector/stack/customer |
| 16 | Stage 2: Harmonization & Stack assembly (Gold) | two-step approach; the harmonize surface; first-class stack; semantic mapping; AI harmonization |
| 17 | Semantic & output validation + failure viz | meaningful validation (clicks ≤ impressions); min/max/mean; visualize failures |
| 18 | In-app sandbox / test environment | a safe place to test configs |
| 19 | RBAC enhancements + role management UI | improved RBAC |
| 20 | Dashboard revamp + live pipeline monitoring | monitor runs; better dashboard |
| 21 | Tenant-scoped extensibility & flexibility | add dimensions/layouts/checks per customer |

### 4.1 Phase 14 — Config-driven I/O paths & destinations
A versioned, config-as-data **`io_profile`** (per-tenant, with a global default)
declares logical roots — `input`, `output`, `temp`, `archive`, `error`, `reject`
— backed by env defaults in `core/config.py` and an overridable DB row (paths are
data, not code — **CC-14**). Generating a Stack writes to the configured `output`
path via the existing `ObjectStorage` abstraction **in addition to** the browser
CSV download. A file lifecycle moves processed inputs to `archive` on success and
`error` on failure; validation-rejected rows/files go to `reject`; scratch lives
in `temp` — all recorded on `job_event` (CC-3/CC-7). Immutable-raw (CC-2) is
preserved: originals stay in immutable storage; the lifecycle acts on copies.

### 4.2 Phase 15 — Universal clone / duplicate
One consistent **Duplicate** affordance on every reusable entity — `MappingConfig`,
`RuleSet` (+ `Rule`s), `FeedTemplate`, `ConnectorConfig` (config only — **never**
credentials/secrets, CC-10/CC-12), `Stack`, and a whole **customer/workspace**
setup. Clone semantics: deep copy → new UUID(s), `version=1`,
`lifecycle_status="draft"`, `created_by=<actor>`, a `cloned_from` provenance
pointer; audited; tenant-scoped writes (cross-tenant clone is an explicit ADMIN
action). Never clones secrets, sessions, audit records, or output rows.

### 4.3 Phase 16 — Stage 2: Harmonization & Stack assembly (Gold)
The new second stage/surface (§2). Sub-phases: **16.1** the `Stack`/`StackRow`
entities + assembly of multiple Silver outputs into one panel; **16.2** the
config-as-data harmonization engine (taxonomy/value harmonization, semantic field
mapping, currency/timezone/attribution reconciliation, entity resolution);
**16.3** AI-assisted harmonization (suggest-not-decide, CC-5, metered by CC-13).

### 4.4 Phase 17 — Semantic & output validation + failure visualization
See the full catalog in §5. Semantic (cross-field) checks are the "meaningful
validation" ask; output statistics (min/max/mean/…) are computed on the Stack and
shown before publish; the validation UI gains distribution/failure visualization.

### 4.5 Phase 18 — In-app sandbox / test environment
A **sandbox run**: pick a config *draft* + a sample or real file and run the full
pipeline **without publishing** — coverage, transform preview, validation flags,
and output stats, all throwaway (a flag on `job`, excluded from real output/
stacks, auto-expiring via retention). Builds on the existing draft→publish
lifecycle and preview engine. Clearly badged so sandbox output is never mistaken
for a published stack.

### 4.6 Phase 19 — RBAC enhancements + role management UI
Add a distinct **`approver`** role (review/publish without config authorship) and
a **`platform_admin`** role (customer/tenant management — today reuses ADMIN),
and optionally an **`APPROVE`** permission distinct from `WRITE_CONFIG` for
draft→publish gating. Keep the matrix small (≤6 roles), deny-by-default. Add a
role-management UI in the Admin console (assign roles, view the role→permission
matrix, per-user audit). No custom per-resource ACLs in v1 (avoids role
explosion).

### 4.7 Phase 20 — Dashboard revamp + live pipeline monitoring
Add polling/SSE auto-refresh so in-flight jobs/syncs update live in the runs view
(reusing `job_event` + `GET /jobs/{id}`; no new backend model). Add a tenant-level
KPI/analytics dashboard (stacks published, data-quality trend, open flags by
severity, files processed, failures over time, connector sync health).

### 4.8 Phase 21 — Tenant-scoped extensibility & flexibility
The "add dimensions / layouts per customer" ask, and the overarching flexibility
principle. See §6.

---

## 5. The validation catalog (Phase 17)

Validation gains a **semantic** family — checks that catch data errors by making
sense of the data — plus **output statistics**. Checks are config-as-data (tenants
tune severity) and tenant-extensible (custom checks, Phase 21). Organized by the
six data-quality dimensions, with MMM specifics and cross-source (Gold) checks.

| Dimension | Checks |
|---|---|
| **Completeness** | required fields present; per-field null-rate thresholds; **date-grid completeness** (no missing periods at grain); expected-channel coverage |
| **Uniqueness** | duplicate rows *(exists)*; duplicate `(date × dimensions)` key; duplicate campaign across sources |
| **Consistency (cross-field / semantic)** | **funnel monotonicity** — `clicks ≤ impressions`, `conversions ≤ clicks`, `reach ≤ impressions`; **CTR** within a plausible band; **CVR** within a band; **CPC / CPM** sanity; spend↔delivery coherence (`spend > 0 ⇒ impressions > 0`); revenue↔conversion coherence |
| **Validity** | value ∈ canonical taxonomy (e.g. `channel` in the allowed set); type/format; range (measures ≥ 0; `date` within the reporting window); ISO-4217 currency code |
| **Timeliness / continuity** | grain-aware date continuity *(exists)*; **freshness** (latest date not stale); **week-over-week spike/drop** anomaly |
| **Accuracy / reasonableness** | statistical outliers via z-score/IQR *(exists)*; zero / near-constant series; unit & magnitude sanity; **mixed-currency detection** (pre-harmonization) |
| **Cross-source (Gold / panel)** | **total-spend reconciliation** across sources within ±X% of a reference; taxonomy completeness (every source value mapped); duplicate-source overlap; attribution-window consistency; currency/timezone alignment |

**Output statistics.** Per measure: **min / max / mean / median / stddev /
null-rate / row-count**, plus week-over-week deltas — computed on the Stack and
shown before publish (extends the existing `anomaly.py`).

**Layering.** Per-source (Silver) checks run in Stage 1; cross-source/panel (Gold)
checks run before a Stack can publish (**CC-15**). Cross-source coherence (spend
reconciliation, taxonomy completeness, duplicate-source overlap) is inherently
Gold.

**Failure visualization.** The validation review UI gains a distribution/spark
view of failing rows per check plus a stats table. This is the platform's first
charting need; the front-end has no charting library today, so the phase makes an
explicit bespoke-SVG-vs-add-a-lib decision under the existing token system
([`../../front-end/CLAUDE.md`](../../front-end/CLAUDE.md)).

---

## 6. Extensibility & flexibility model (Phase 21)

The overarching principle: **everything is metadata-driven config-as-data, layered
global → template → customer, so a customer can extend the platform without code.**

**Chosen approach — metadata registry + JSON extension columns** (not EAV, not
schema-per-tenant; **ADR-015**). The canonical schema stays a fixed **core
contract**. Per-tenant additions live in a versioned **`schema_extension`**
registry (`tenant_id`, `kind` = dimension | measure | factor, `name`, `data_type`,
`taxonomy_ref`, `validation`, `layer`, `version`, `lifecycle_status`). Extension
*values* need **no migration** because `OutputRow.data` / `StackRow` are already
JSON blobs — a custom field is just an extra key. This is the modern multi-tenant
pattern (JSON + a metadata-aware app layer) and stays SQLite→Postgres portable.

- **Custom dimensions / measures / factors** per workspace auto-appear everywhere,
  because the UI and engines read the *resolved* schema (core + tenant extensions):
  mapping targets, transform targets, validation, stack columns, export contract.
  "Add a dimension" = a registry row, zero code.
- **Custom layouts / views** scoped to workspace: saved column layouts, ordering,
  and view presets for tables/mapping/stack browser. (Input layouts already exist
  as `FeedTemplate`; this adds output/stack layouts + saved UI views.)
- **Custom validation checks** scoped to workspace: expression-based checks as
  config-as-data via the existing sandboxed DSL (ADR-004) — a tenant writes
  `clicks <= impressions`-style rules safely, without code.
- **Metadata-driven UI**: components render fields from the resolved schema, not
  hardcoded lists.
- **Semantic-layer framing (north star)**: canonical core + tenant extensions +
  the Stack contract together form a *governed semantic layer* the modelling step
  and AI consume via the export-contract API (headless-BI style, à la dbt/Cube).
  Documented as direction, not built now.

---

## 7. Usability principles applied (from research)

- **Two focused stages, not one overloaded pipeline** (medallion) — reduces
  cognitive load; matches how MMM data prep actually splits.
- **AI-assisted harmonization, human-ratified** (taxonomy/entity resolution) — AI
  proposes; humans approve (CC-5). Scoped to Stage 2.
- **Live pipeline health** (running/failed/duration, per-stage timeline, retries)
  — data-observability best practice; Phase 20.
- **One consistent "Duplicate" affordance** everywhere — predictable, low-surprise;
  Phase 15.
- **Meaningful (semantic) validation over structural** — schema checks alone miss
  business-rule errors; cross-field + ratio checks catch real data errors; Phase 17.
- **Config-as-data & no raw JSON to users** — every new surface authors versioned
  config behind the scenes (existing product principle).
- **Safe experimentation before commit** (sandbox + draft→publish) — Phase 18.
- **Small, documented RBAC** (3–6 roles, deny-by-default) — Phase 19.
- **Metadata-driven flexibility** — extend via versioned config; the UI/engines
  render from the resolved schema; no code per customer — Phase 21.

---

## 8. Cross-cutting conformance

All eight workstreams uphold the existing invariants (CC-1…CC-13) and introduce
two new ones (added to [`../build-plan.md`](../build-plan.md) §2):

- **CC-14 Config-driven I/O:** input/output/temp/archive/error/reject paths and
  export destinations come from **versioned config**, never hardcoded; immutable-raw
  (CC-2) still holds — the lifecycle acts on copies, never the raw original.
- **CC-15 Semantic integrity:** cross-field business-rule checks (funnel
  monotonicity, ratio sanity, coherence) and cross-source panel checks run and are
  gated before a Stack can publish.

Notable per-phase conformance: CC-1 (every new record tenant-scoped: `io_profile`,
`schema_extension`, `Stack`, `StackRow`, sandbox jobs, layouts); CC-3 (Stack
lineage Gold→Silver→Bronze; clone `cloned_from`); CC-4 (io_profile, harmonization
rules, semantic map, schema extensions, custom checks are all versioned config);
CC-5 (AI harmonization only suggests); CC-6 (Stack publish idempotent);
CC-10/CC-12 (clone never copies credentials/secrets).

---

## 9. Open questions (registered in [`../open-questions.md`](../open-questions.md))

- **OQ-14.1** io_profile scope — global default + per-tenant override; per-connector paths in v1?
- **OQ-14.2** file lifecycle — move vs copy to archive/error/reject (default: copy, to preserve immutability).
- **OQ-16.1** Stack scope — a Stack aggregates multiple Silver outputs (confirmed); max sources per stack; incremental append vs full rebuild on re-publish?
- **OQ-16.2** harmonization rules vs Stage-1 rule sets — a separate config family (recommended) vs reusing `RuleSet` with a scope flag?
- **OQ-16.3** AI harmonization — deterministic alias table first, LLM only for the residual; auto-suggest vs require-review confidence threshold.
- **OQ-17.1** CTR/CPC/CPM plausibility bounds — default bands + per-tenant override.
- **OQ-17.2** charting — bespoke SVG vs the first charting dependency (respect the design system).
- **OQ-18.1** sandbox data — sample fixtures vs real files; retention/expiry of sandbox runs.
- **OQ-19.1** approve/publish as a permission distinct from `write_config` — needed now?
- **OQ-21.1** extension storage — JSON columns + metadata registry (recommended) vs EAV vs per-tenant schema; portability + query needs.
- **OQ-21.2** do custom dimensions participate in anomaly slicing / required-field gates, or advisory only by default?
- **OQ-21.3** custom-check safety — bound the DSL and cap checks per tenant.
- **OQ-21.4** how far to formalize the semantic-layer/headless-BI framing now vs later.

---

## 10. Build order & phase map

Cycle 5 phases are added to the authoritative build order in
[`../phases/README.md`](../phases/README.md) with Status **Build**. Suggested
sequence (dependencies in parentheses):

1. **14** Config-driven I/O *(independent; unblocks destination export used by 16)*
2. **17** Semantic & output validation *(independent; used as the Stack publish gate)*
3. **21** Extensibility *(schema-resolution layer that 16/17 read)*
4. **16** Stage-2 Harmonization & Stack assembly *(depends 14, 17, 21)*
5. **15** Universal clone *(depends 16 for Stack clone; rest independent)*
6. **19** RBAC enhancements *(gates Stack publish/approve)*
7. **18** In-app sandbox *(builds on preview + draft lifecycle)*
8. **20** Dashboard & live monitoring *(reads Stacks + runs; do last)*

Order is guidance, not a hard chain — 14, 17, 19, 20 are largely independent and
can proceed in parallel across contributors. Each ships one phase per PR with a
linked spec + acceptance checklist.

---

_Living document — refine as each phase spec is deepened before it is built._
