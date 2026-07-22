# Phase Index

The platform is built **strictly phase by phase, in order**. Do not start a phase
until the prior phase's acceptance criteria pass. Each phase spec derives from
[`../build-plan.md`](../build-plan.md) and honours the cross-cutting requirements
(CC-1…CC-10) documented there.

Before working on a phase, read its spec **and the spec(s) it depends on**, plus
the relevant items in [`../open-questions.md`](../open-questions.md).

## MVP

**The MVP is Phases 0–4** (file in → clean data out, config-driven). Phase 5 (AI)
and Phase 6 (UI) make it usable; Phases 7–8 make it enterprise-ready; Phase 9 is
explicitly future/deferred.

## Phases

| Phase | Spec | One-line summary | Depends on | Status |
|---|---|---|---|---|
| 0 | [phase-00](./phase-00-foundations-canonical-schema-data-model.md) | Repo, canonical schema, taxonomies, data model, tenancy model. | — | Done, pending merge ([00.1](./phase-00.1-canonical-schema-taxonomies.md)/[00.2](./phase-00.2-data-model-migrations.md)/[00.3](./phase-00.3-tenancy-config-versioning.md)) |
| 1 | [phase-01](./phase-01-file-ingestion-structure-detection.md) | Land files immutably; parse CSV/multi-tab XLSX; detect structure; profile. | 0 | Done, pending merge ([01.1](./phase-01.1-object-storage-ingestion.md)/[01.2](./phase-01.2-parsing-structure-detection.md)/[01.3](./phase-01.3-profiling.md)) |
| 2 | [phase-02](./phase-02-mapping-engine-saved-configs.md) | Map columns to canonical schema; reusable, layered, versioned saved configs. | 0, 1 | Done, pending merge ([02.1](./phase-02.1-mapping-engine.md)/[02.2](./phase-02.2-saved-configs-matching.md)) |
| 3 | [phase-03](./phase-03-transformation-rule-engine.md) | Declarative, ordered, layered transformation rules with before/after preview. | 0, 2 | Done, pending merge ([03.1](./phase-03.1-rule-engine-core.md)/[03.2](./phase-03.2-value-ops-preview-api.md)) |
| 4 | [phase-04](./phase-04-validation-anomaly-detection.md) | Quality checks + anomaly detection; flag issues for human review. | 1, 2, 3 | Done, pending merge ([04.1](./phase-04.1-validation-engine.md)/[04.2](./phase-04.2-anomaly-review-api.md)) |
| 5 | [phase-05](./phase-05-ai-suggestion-layer.md) | AI drafts mappings/labels/structure/anomaly explanations; humans ratify. | 2, 3, 4 | Done, pending merge ([05.1](./phase-05.1-llm-provider-config.md)/[05.2](./phase-05.2-suggestion-service-api.md)) |
| 6 | [phase-06](./phase-06-review-ui-nextjs.md) | Next.js review UI: dashboards, mapping review, transformation builder, validation review. | 2–5 | Not started |
| 7 | [phase-07](./phase-07-multitenancy-async-scale.md) | Queue + workers; batch fan-out; per-tenant fairness; isolation hardening; observability. | all above | Not started |
| 8 | [phase-08](./phase-08-governance-security.md) | RBAC, audit logging, encryption, admin UI. | 7 | Not started |
| 9 | [phase-09](./phase-09-future-connectors-extraction.md) | *(Future)* Partner data connectors (SFTP + Meta/Google Ads/DV360/TikTok); PDF/email extraction. Fully designed (09.1–09.8); 09.1 realised as the Phase-1 source seam. | 0–8 (+ Phase 1 seam) | Deferred |

## Phase 9 sub-phases (deferred; fully designed)

Phase 9 (partner data connectors) is broken into sub-phases now so it attaches to
the existing source seam without a refactor. **09.1 is foundational** — it is the
source-agnostic abstraction that is **already realised in code** as the Phase-1
seam (`src/mmm_os/sources/`), and is referenced by
[phase-01](./phase-01-file-ingestion-structure-detection.md).

- [09.1](./phase-09.1-source-abstraction-landed-dataset.md) — source abstraction + landed dataset *(foundational; realised in Phase 1)*.
- [09.2](./phase-09.2-connector-framework-credentials.md) — connector framework + OAuth/credentials.
- [09.3](./phase-09.3-sftp-source.md) — SFTP file source.
- [09.4](./phase-09.4-partner-connector-meta.md) — Meta reference connector.
- [09.5](./phase-09.5-partner-connectors-google-dv360-tiktok.md) — Google Ads / DV360 / TikTok.
- [09.6](./phase-09.6-scheduling-incremental-backfill.md) — scheduling, incremental, backfill.
- [09.7](./phase-09.7-partner-mapping-taxonomy-templates.md) — per-partner mapping/taxonomy templates.
- [09.8](./phase-09.8-connector-observability-admin.md) — connector observability + admin.

PDF/email extraction is preserved as a **separate deferred sub-track** in the
Phase-9 spec.

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
