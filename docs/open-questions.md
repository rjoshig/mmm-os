# Open Questions

**Status:** v0.2 — many questions resolved during the foundations exercise.
**Rule:** where a question is still **Open**, stop and ask rather than assuming
(see [`../CLAUDE.md`](../CLAUDE.md), golden rule 4). Resolutions below are
recorded here and, where architectural, in [`architecture.md`](./architecture.md)
(ADR log); schema-affecting ones in [`canonical-schema.md`](./canonical-schema.md).

**Legend:** ✅ Resolved · 🟡 Partially resolved · ⏸️ Deferred (with a leaning).

---

## Appendix E — Consolidated Open Questions (from the source docs)

| ID | Question | Phase | Status |
|---|---|---|---|
| OQ-0.1 | Tenant isolation: row-level vs schema/DB-per-tenant. | 0 | ✅ **Row-level** (`tenant_id` on every domain table). See ADR-003. |
| OQ-0.2 | Warehouse choice for clean output. | 0 | ✅ **v1 = an `output_row` table in the backend DB** (SQLite→Postgres); dedicated warehouse deferred until scale. See ADR-005. |
| OQ-1.1 | Max file size / row count for v1. | 1 | ✅ **~200 MB / ~5M rows per sheet** as the documented v1 ceiling; streamed/chunked; configurable; over-limit files fail the job with a clear reason. |
| OQ-1.2 | Multiple header-like rows behaviour (pick vs ask). | 1 | ✅ **Pick + flag**: auto-select the highest-scoring header deterministically; below a confidence threshold, flag `needs-review` (AI assists in Phase 5). |
| OQ-2.1 | Column-signature definition (exact/fuzzy/positional). | 2 | ✅ **Normalized header-name set** (lowercased, trimmed, whitespace/punctuation-collapsed), order-tolerant; match = exact set equality. Fuzzy/positional matching deferred to the AI layer (Phase 5). |
| OQ-2.2 | Required vs optional canonical fields / measures. | 2 | ✅ **Required: `date` + `channel` + ≥1 measure**; all other fields optional. See canonical-schema A.4. |
| OQ-3.1 | Escape-hatch `custom` rule scope. | 3 | ✅ **Sandboxed expression language** (restricted DSL over row/field context; no arbitrary code, imports, or I/O; allowlisted ops; resource-bounded). See ADR-004. |
| OQ-3.2 | Reshape (wide→long) config model. | 3 | ✅ **Draft config model** `{ id_vars, value_vars \| value_var_pattern, var_name → dimension, value_name → measure }`; deterministic. |
| OQ-4.1 | Default severity / blocking policy. | 4 | ✅ **BLOCK** = missing/unmapped required field, negative measure, type mismatch on a required field; **WARN** = date gaps, duplicates, outliers, out-of-range non-required. Configurable per tenant. |
| OQ-4.2 | Anomaly method for v1. | 4 | ✅ **z-score (robust/median variant) + IQR** per dimension slice; behind a pluggable detector interface. |
| OQ-5.1 | LLM provider / model + cost ceiling per file. | 5 | 🟡 **Provider = Claude (Anthropic API)**, most-capable model, behind a provider abstraction. **Cost ceiling per file deferred** (needs real usage data). See ADR-008. |
| OQ-5.2 | Confidence calibration. | 5 | ⏸️ **Deferred** — needs labelled accept/reject data. Interim: model-reported confidence + configurable thresholds; calibrate later (reliability curves / isotonic). |
| OQ-6.1 | Design system / component library. | 6 | ✅ **Extracted design language + hand-built shadcn-style primitives** (Card/Badge/Table/PageHeader/StatCard); no heavy third-party component library. See ADR-009 and `../front-end/CLAUDE.md`. |
| OQ-7.1 | Queue tech + worker hosting. | 7 | ✅ **Celery + Redis** (broker + result backend); autoscaling workers; per-tenant rate limiting/fairness. See ADR-007. |
| OQ-8.1 | Target compliance framework. | 8 | ⏸️ **Deferred** — working target **SOC 2 Type II** (per PRD); specific controls/scope to be set in Phase 8 with legal. |

---

## Questions surfaced during repository initialization

| ID | Question | Phase | Status |
|---|---|---|---|
| OQ-INIT.1 | Object-storage provider and local-dev substitute. | 1 | ✅ **Storage abstraction**: local filesystem in dev, S3-compatible (S3/MinIO) in prod, selected by env. See ADR-006. |
| OQ-INIT.2 | Is the clean-output "warehouse" a backend-DB table or a separate system for v1? | 0/1 | ✅ **Backend-DB table** (`output_row`) for v1 — same decision as OQ-0.2. See ADR-005. |
| OQ-INIT.3 | Does the UI (Prisma) database store anything beyond front-end concerns? | 6 | ✅ **UI-only concerns** (session/preferences/UI state later); never mirrors backend domain data; effectively empty until Phase 6. |
| OQ-INIT.4 | LLM provider/SDK choice and credential injection. | 5 | ✅ **Anthropic SDK; credentials via env (`ANTHROPIC_API_KEY`)**; only profile data sent to the model (P5-1). Folds into ADR-008. |

---

## Still open (need input before their phase)

- **OQ-5.1 (cost ceiling per file)** — set once we have real per-file token/cost data.
- **OQ-5.2 (confidence calibration)** — needs labelled accept/reject outcomes.
- **OQ-8.1 (compliance controls)** — SOC 2 Type II is the working target; confirm scope + controls with legal in Phase 8.

---

## Decisions already locked (for reference)

Recorded in [`architecture.md`](./architecture.md) (ADR log) and the relevant docs:

- Two independent databases (backend + UI), each SQLite now / Postgres later, swappable by config only (ADR-001, ADR-002).
- **Row-level tenant isolation** — `tenant_id` on every domain table (ADR-003, OQ-0.1).
- **Clean output v1 = `output_row` table in the backend DB** (ADR-005, OQ-0.2/INIT.2).
- **Object storage = abstraction; local FS dev / S3-compatible prod** (ADR-006, OQ-INIT.1).
- **Transformation `custom` op = sandboxed expression language** (ADR-004, OQ-3.1).
- **Async queue = Celery + Redis** (ADR-007, OQ-7.1).
- **AI provider = Claude via the Anthropic API**, env-injected creds, profile-only inputs (ADR-008, OQ-5.1/INIT.4).
- **Design system = extracted tokens + hand-built shadcn-style primitives** (ADR-009, OQ-6.1).
- Required canonical fields: `date` + `channel` + ≥1 measure (OQ-2.2).
- Python targets **3.10+**; backend SQLAlchemy 2.0 + Alembic; UI Prisma.
- Front-end design language replicated from the reference UI (`../front-end/CLAUDE.md`).

---

_Living document — when a still-open question is answered, move it up with a
pointer to the ADR / phase spec that records the decision._
