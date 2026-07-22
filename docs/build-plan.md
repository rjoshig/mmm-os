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
| **9** | Connectors & Extraction | Partner data connectors (SFTP + Meta/Google/DV360/TikTok); PDF/email extraction *(deferred sub-track)* | 0–8 |

Additional phases (added post-v0.1 for enterprise readiness) are listed
authoritatively in [`phases/README.md`](./phases/README.md): inserted **Build**
phases 00.5, 00.6, 05.1, 07.1, 07.2, 08.1 and **Spec-only** tail phases 10, 11, 12.

**Guiding principle:** the MVP is **Phases 0–4** (file in → clean data out,
config-driven). Phase 5 (AI) and Phase 6 (UI) make it usable; the enterprise-
readiness phases (00.5/00.6/05.1/07.1/07.2/08.1 + 7/8) make it production-grade;
Phase 9 (connectors) is planned but sequenced last, and Phases 10–12 are
design-only.

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
- **CC-3 Traceability:** every output row MUST be traceable to its **source** (source file + sheet + row for file sources; `source`/`sync_run` for API connectors) + applied rule versions — a source-agnostic trace (CC-9, ADR-010).
- **CC-4 Config-as-data:** all mappings and transformations MUST be stored as data (not code), versioned.
- **CC-5 Human-in-the-loop:** AI never auto-commits; suggestions require human accept/reject/modify.
- **CC-6 Idempotent jobs:** re-running a job on the same input MUST produce the same result and not duplicate output (for connectors: re-pulling a window **replaces**, never duplicates).
- **CC-7 Observability:** every job stage MUST emit status + timing + error records.
- **CC-8 Stack:** Next.js (frontend) · FastAPI/Python (API) · Celery/RQ (workers) · Postgres (metadata/config; SQLite in dev) · object storage (raw files) · warehouse (clean output) · LLM (suggestions).
- **CC-9 Source-agnostic pipeline:** mapping, transform, validation, and output MUST operate on the common **landed representation** regardless of source (upload / SFTP / API connector). Sources implement one `SourceConnector` contract producing a `LandedDataset` (ADR-010).
- **CC-10 Credential security:** partner credentials/tokens MUST be encrypted at rest, tenant-scoped, least-privilege (read-only reporting scopes), and **never logged**.
- **CC-11 Authenticated access:** every API endpoint MUST require authenticated + authorized (tenant-scoped) access — no anonymous reach into any tenant's data. See [`phases/phase-00.5-authentication-identity.md`](./phases/phase-00.5-authentication-identity.md).
- **CC-12 Secrets via store:** all secrets/tokens (app secrets, auth/IdP secrets, partner OAuth tokens) MUST go through the `SecretStore` — never plaintext at rest, never logged. See [`phases/phase-00.6-secrets-management.md`](./phases/phase-00.6-secrets-management.md).
- **CC-13 LLM budget enforcement:** LLM usage MUST be metered per tenant and respect configured budgets/caps. See [`phases/phase-05.1-llm-cost-controls.md`](./phases/phase-05.1-llm-cost-controls.md).

---

## 3. Phase index

> The table below lists the **original** phases 0–9. Additional **inserted**
> phases (00.5, 00.6, 05.1, 07.1, 07.2, 08.1) and **spec-only tail** phases
> (10, 11, 12) were added for enterprise readiness. **[`phases/README.md`](./phases/README.md)
> is the authoritative source for the full build order + per-phase Status
> (Build / Spec-only / Deferred).**

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
| 9 | [`phases/phase-09-future-connectors-extraction.md`](./phases/phase-09-future-connectors-extraction.md) | Build (sequenced last; PDF/email sub-track deferred) |

---

_This is a living document — each phase spec will be deepened before that phase is
implemented._
