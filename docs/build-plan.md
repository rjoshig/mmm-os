# Build Plan
## Marketing Data Ingestion & Transformation Platform

**Companion to:** [`prd.md`](./prd.md) (read that first for background & rationale).
**Status:** Draft v0.1 — requirements & documentation only (no implementation yet).
**Purpose:** the source of truth for building the platform **phase by phase**.

---

## How to use this document

- Build **strictly phase by phase, in order.** Do not start a later phase until the prior phase's acceptance criteria pass.
- Each phase's detailed spec lives in [`phases/`](./phases/), with: **Objective · Scope (in/out) · Functional Requirements · Deliverables · Acceptance Criteria · Dependencies · Open Questions.**
- **Do not** implement anything marked *Deferred* or in *Out of Scope* unless explicitly told.
- Treat the **Canonical Schema** ([`canonical-schema.md`](./canonical-schema.md)) as the fixed target contract — mapping, rules, and AI suggestions all resolve to it.
- Where an **Open Question** exists ([`open-questions.md`](./open-questions.md)), stop and ask rather than assuming.
- Requirements use **MUST / SHOULD / MAY** (RFC-2119 sense).

---

## 1. High-Level Phase Roadmap

| Phase | Name | Outcome | Depends on |
|---|---|---|---|
| **0** | Foundations, Canonical Schema & Data Model | Repo, schema, DB tables, tenancy model decided | — |
| **1** | File Ingestion & Structure Detection | Files land, get parsed (multi-tab), profiled | 0 |
| **2** | Mapping Engine & Saved Configs | Columns map to canonical schema; configs reused | 0, 1 |
| **3** | Transformation Rule Engine | Declarative rules transform data with preview | 0, 2 |
| **4** | Validation & Anomaly Detection | Quality checks flag issues for review | 1, 2, 3 |
| **5** | AI Suggestion Layer | AI drafts mappings/labels/structure; human ratifies | 2, 3, 4 |
| **6** | Review UI (Next.js) | Mapping tables, preview, approve/reject, dashboards | 2–5 |
| **7** | Multi-Tenancy, Async & Scale | Queue, workers, isolation hardening, observability | all above |
| **8** | Governance & Security | Roles, audit, encryption, compliance | 7 |
| **9** | *(Future)* Connectors & Extraction | API connectors; PDF/email extraction | deferred |

**Guiding principle:** the MVP is **Phases 0–4** (file in → clean data out,
config-driven). Phase 5 (AI) and Phase 6 (UI) make it usable; Phases 7–8 make it
enterprise-ready. Phase 9 is explicitly future.

**Baked-in-from-day-one note:** tenant isolation (`tenant_id` on every table) and
async-ready job records MUST be scaffolded in Phase 0 even though scale-hardening
happens in Phase 7. This decision is hard to reverse.

Per-phase specs: see [`phases/README.md`](./phases/README.md) for the index and
the sub-phase naming convention.

---

## 2. Cross-Cutting Requirements (apply to every phase)

These are invariants. Every phase must uphold them; PRs should reference the
relevant `CC-n` where applicable.

- **CC-1 Multi-tenant:** every persisted record MUST carry `tenant_id`; no query may return cross-tenant data.
- **CC-2 Immutable raw:** original uploaded files MUST be stored unaltered; all processing works on copies/derived data.
- **CC-3 Traceability:** every output row MUST be traceable to source file + sheet + row + applied rule versions.
- **CC-4 Config-as-data:** all mappings and transformations MUST be stored as data (not code), versioned.
- **CC-5 Human-in-the-loop:** AI never auto-commits; suggestions require human accept/reject/modify.
- **CC-6 Idempotent jobs:** re-running a job on the same input MUST produce the same result and not duplicate output.
- **CC-7 Observability:** every job stage MUST emit status + timing + error records.
- **CC-8 Stack:** Next.js (frontend) · FastAPI/Python (API) · Celery/RQ (workers) · Postgres (metadata/config; SQLite in dev) · object storage (raw files) · warehouse (clean output) · LLM (suggestions).

---

## 3. Phase index

| Phase | Spec file | Status |
|---|---|---|
| 0 | [`phases/phase-00-foundations-canonical-schema-data-model.md`](./phases/phase-00-foundations-canonical-schema-data-model.md) | Not started |
| 1 | [`phases/phase-01-file-ingestion-structure-detection.md`](./phases/phase-01-file-ingestion-structure-detection.md) | Not started |
| 2 | [`phases/phase-02-mapping-engine-saved-configs.md`](./phases/phase-02-mapping-engine-saved-configs.md) | Not started |
| 3 | [`phases/phase-03-transformation-rule-engine.md`](./phases/phase-03-transformation-rule-engine.md) | Not started |
| 4 | [`phases/phase-04-validation-anomaly-detection.md`](./phases/phase-04-validation-anomaly-detection.md) | Not started |
| 5 | [`phases/phase-05-ai-suggestion-layer.md`](./phases/phase-05-ai-suggestion-layer.md) | Not started |
| 6 | [`phases/phase-06-review-ui-nextjs.md`](./phases/phase-06-review-ui-nextjs.md) | Not started |
| 7 | [`phases/phase-07-multitenancy-async-scale.md`](./phases/phase-07-multitenancy-async-scale.md) | Not started |
| 8 | [`phases/phase-08-governance-security.md`](./phases/phase-08-governance-security.md) | Not started |
| 9 | [`phases/phase-09-future-connectors-extraction.md`](./phases/phase-09-future-connectors-extraction.md) | Deferred |

---

_This is a living document — each phase spec will be deepened before that phase is
implemented._
