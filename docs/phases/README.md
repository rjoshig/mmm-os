# Phase Index

The platform is built **strictly phase by phase, in order**. Do not start a phase
until the prior phase's acceptance criteria pass. Each phase spec derives from
[`../build-plan.md`](../build-plan.md) and honours the cross-cutting requirements
(CC-1…CC-8) documented there.

Before working on a phase, read its spec **and the spec(s) it depends on**, plus
the relevant items in [`../open-questions.md`](../open-questions.md).

## MVP

**The MVP is Phases 0–4** (file in → clean data out, config-driven). Phase 5 (AI)
and Phase 6 (UI) make it usable; Phases 7–8 make it enterprise-ready; Phase 9 is
explicitly future/deferred.

## Phases

| Phase | Spec | One-line summary | Depends on | Status |
|---|---|---|---|---|
| 0 | [phase-00](./phase-00-foundations-canonical-schema-data-model.md) | Repo, canonical schema, taxonomies, data model, tenancy model. | — | Not started |
| 1 | [phase-01](./phase-01-file-ingestion-structure-detection.md) | Land files immutably; parse CSV/multi-tab XLSX; detect structure; profile. | 0 | Not started |
| 2 | [phase-02](./phase-02-mapping-engine-saved-configs.md) | Map columns to canonical schema; reusable, layered, versioned saved configs. | 0, 1 | Not started |
| 3 | [phase-03](./phase-03-transformation-rule-engine.md) | Declarative, ordered, layered transformation rules with before/after preview. | 0, 2 | Not started |
| 4 | [phase-04](./phase-04-validation-anomaly-detection.md) | Quality checks + anomaly detection; flag issues for human review. | 1, 2, 3 | Not started |
| 5 | [phase-05](./phase-05-ai-suggestion-layer.md) | AI drafts mappings/labels/structure/anomaly explanations; humans ratify. | 2, 3, 4 | Not started |
| 6 | [phase-06](./phase-06-review-ui-nextjs.md) | Next.js review UI: dashboards, mapping review, transformation builder, validation review. | 2–5 | Not started |
| 7 | [phase-07](./phase-07-multitenancy-async-scale.md) | Queue + workers; batch fan-out; per-tenant fairness; isolation hardening; observability. | all above | Not started |
| 8 | [phase-08](./phase-08-governance-security.md) | RBAC, audit logging, encryption, admin UI. | 7 | Not started |
| 9 | [phase-09](./phase-09-future-connectors-extraction.md) | *(Future)* API connectors; PDF/email extraction. | deferred | Deferred |

## Sub-phase convention

When a phase is too large to implement in one pass, break it into **sub-phases**:

- Add a file named **`phase-NN.M-slug.md`** in this directory, where `NN` is the
  zero-padded phase number and `M` is the sub-phase index — e.g.
  `phase-01.1-object-storage.md`, `phase-01.2-structure-detection.md`.
- **Link each sub-phase file** from the parent phase's **`## Sub-phases`** section
  (replace its `TBD` placeholder with the list of links).
- Keep the same section structure (Objective · Scope · Functional Requirements ·
  Deliverables · Acceptance Criteria · Dependencies · Open Questions) in each
  sub-phase spec.
- **Numbering stays zero-padded** so lexical ordering matches phase ordering.
- Per [`../../GIT_STANDARDS.md`](../../GIT_STANDARDS.md): **one sub-phase per
  branch/PR** once a phase is broken down (one phase per PR otherwise).

## Status legend

- **Not started** — spec written; no implementation.
- **In progress** — implementation underway on a phase/sub-phase branch.
- **Done** — all acceptance criteria pass and merged.
- **Deferred** — explicitly out of scope until scoped (Phase 9).
