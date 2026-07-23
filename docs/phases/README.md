# Phase Index

The platform is built **strictly phase by phase, in order**. Do not start a phase
until the prior phase's acceptance criteria pass. Each phase spec derives from
[`../build-plan.md`](../build-plan.md) and honours the cross-cutting requirements
(CC-1…CC-13) documented there.

Before working on a phase, read its spec **and the spec(s) it depends on**, plus
the relevant items in [`../open-questions.md`](../open-questions.md).

**This file is the authoritative source for build order + per-phase Status.** The
sequence below interleaves the original phases with **inserted** enterprise-
readiness phases (decimal filenames — standalone phases, *not* sub-phases) and
**spec-only** tail phases (10–12).

## MVP

**The MVP is Phases 0–4** (file in → clean data out, config-driven). Phase 5 (AI)
and Phase 6 (UI) make it usable; the enterprise-readiness phases (00.5/00.6/05.1/
07.1/07.2/08.1 + 7/8) make it production-grade; Phase 9 (connectors) is fully
designed but deferred; Phases 10–12 are design-only.

## Build order (authoritative)

Status: **Build** = to be implemented · **Done** = implemented, pending merge ·
**Spec-only** = designed, not scheduled to build · **Deferred** = out of scope
until scoped.

| # | Phase | Spec | One-line summary | Depends on | Status |
|---|---|---|---|---|---|
| 1 | 0 | [phase-00](./phase-00-foundations-canonical-schema-data-model.md) | Repo, canonical schema, taxonomies, data model, tenancy. | — | Done |
| 2 | 00.5 | [phase-00.5](./phase-00.5-authentication-identity.md) | Auth & identity: password login + sessions + endpoint guard + seeded admin (CC-11); MFA/SSO deferred. | 0 | Done |
| 3 | 00.6 | [phase-00.6](./phase-00.6-secrets-management.md) | Secrets management: `SecretStore` + local encrypted-dev backend + `secret_ref` (CC-12). | 0 | Done |
| 4 | 1 | [phase-01](./phase-01-file-ingestion-structure-detection.md) | Land files immutably; parse CSV/multi-tab XLSX; detect structure; profile. | 0 | Done |
| 5 | 2 | [phase-02](./phase-02-mapping-engine-saved-configs.md) | Map columns to canonical schema; layered, versioned saved configs. | 0, 1 | Done |
| 6 | 3 | [phase-03](./phase-03-transformation-rule-engine.md) | Declarative, ordered, layered transformation rules with preview. | 0, 2 | Done |
| 7 | 4 | [phase-04](./phase-04-validation-anomaly-detection.md) | Quality checks + anomaly detection; flag issues for review. | 1, 2, 3 | Done |
| 8 | 5 | [phase-05](./phase-05-ai-suggestion-layer.md) | AI drafts mappings/labels/structure/anomaly; humans ratify. | 2, 3, 4 | Done |
| 9 | 05.1 | [phase-05.1](./phase-05.1-llm-cost-controls.md) | LLM cost controls: per-tenant metering, budgets/caps (429), caching, tier routing (CC-13). | 5 | Done |
| 10 | 6 | [phase-06](./phase-06-review-ui-nextjs.md) | Next.js review UI: dashboards, mapping review, transform builder, validation review, admin console. | 2–5, **00.5** | Done |
| 11 | 7 | [phase-07](./phase-07-multitenancy-async-scale.md) | Queue abstraction + per-tenant fairness + batch fan-out + idempotency + isolation tests (Celery+Redis = prod backend). | all above | Done |
| 12 | 07.1 | [phase-07.1](./phase-07.1-observability-monitoring.md) | Observability: metrics registry + structured context (CC-7); prod backend exports the same signals. | 7 | Done |
| 13 | 07.2 | [phase-07.2](./phase-07.2-resilience-error-handling.md) | Resilience: retry/backoff, circuit breaker; queue bounded retries + DLQ (CC-6). | 7 | Done |
| 14 | 8 | [phase-08](./phase-08-governance-security.md) | RBAC + audit log + admin API; in-transit encryption + admin UI deferred. | 7 | Done |
| 15 | 08.1 | [phase-08.1](./phase-08.1-compliance-controls.md) | Access review + least-privilege self-check + controls matrix. | 8, 00.5, 00.6 | Done |
| 16 | 9 (+09.1–09.8) | [phase-09](./phase-09-future-connectors-extraction.md) | Partner data connectors (SFTP + Meta/Google Ads/DV360/TikTok), full framework with mock partner clients; PDF/email extraction deferred. | 0–8 (+ Phase 1 seam) | Done (connectors); PDF/email Deferred |
| 17 | 10 | [phase-10](./phase-10-data-governance-retention.md) | Data governance & retention, backup/DR, erasure, residency, PII posture. | 0–8 | Spec-only |
| 18 | 11 | [phase-11](./phase-11-deployment-infrastructure.md) | Deployment & infra: environments, CI/CD, IaC, autoscaling, secret injection. | 0–8 | Spec-only |
| 19 | 12 | [phase-12](./phase-12-load-scale-testing.md) | Load/scale test plan for 200–500 tenants + batch concurrency. | 0–8, 11 | Spec-only |
| — | Postgres migration | [architecture §2](../architecture.md) | Swap backend/UI DB SQLite→Postgres by config only (portability already designed). | — | Deferred |

> **Note on Phase 9 status.** Phase 9 was originally *Deferred*; it is now planned
> as **Build** (fully designed across 09.1–09.8) but sequenced after the core +
> enterprise-readiness phases. **PDF/email extraction within Phase 9 stays a
> deferred sub-track.** **Postgres migration remains Deferred** — portability is
> already designed, so it needs no new work.

## Phase 9 sub-phases (built; full framework + mock partner clients)

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

## Inserted phases vs sub-phases

Two different things share the decimal filename form:

- **Sub-phases** (e.g. `phase-01.1`, `phase-09.2`) are PR-sized *slices of their
  parent phase*, linked from the parent's `## Sub-phases` section.
- **Inserted phases** (`phase-00.5`, `phase-00.6`, `phase-05.1-llm-cost-controls`,
  `phase-07.1`, `phase-07.2`, `phase-08.1`) are **standalone phases** placed
  mid-sequence for ordering; they are **not** sub-phases of the adjacent phase. The
  **Build order** table above is the authority on where each sits.

> **Label caution — two things named "05.1".** Phase 5 already has sub-phases
> `phase-05.1-llm-provider-config` and `phase-05.2-suggestion-service-api` (slices
> of Phase 5, already **Done**). The **inserted** phase
> `phase-05.1-llm-cost-controls` is a *separate* standalone phase (Status: Build).
> The filenames differ by slug so there is no file collision; always refer to these
> by **full filename**, not the bare number, to avoid ambiguity.

## Status legend

- **Build** — planned for implementation; spec written, not yet built.
- **Done** — implemented and passing (pending PR merge in this repo).
- **Spec-only** — designed now, **not** scheduled to build (Phases 10–12).
- **Deferred** — out of scope until explicitly scoped (PDF/email sub-track within
  Phase 9; the Postgres migration).
