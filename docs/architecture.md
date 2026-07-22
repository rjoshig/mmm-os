# Architecture

**Status:** Draft v0.1 — foundations. This document records the tech stack, the
**database strategy**, and a running **architecture-decision log**. Keep it
current: when a decision is made or changed, add an entry to the log.

---

## 1. Tech Stack

Per cross-cutting requirement **CC-8**:

| Layer | Choice | Notes |
|---|---|---|
| Front-end | **Next.js** (React, TypeScript, App Router, Tailwind) | In `front-end/`. Rich mapping tables + approve/reject flows. Talks to the backend via API. |
| Backend API | **Python 3.10+ / FastAPI** | Thin routers → services → models/db. Ideal for data work + LLM integration. |
| Workers | **Celery + Redis** | Async batch file processing (introduced in Phase 7). Broker + result backend = Redis. See ADR-007. |
| Backend metadata + config DB | **SQLite now → Postgres later** | SQLAlchemy 2.0 + Alembic. Tenants, files, mappings, jobs, rules. |
| UI DB | **SQLite now → Postgres later** | Prisma. Separate from the backend DB; UI-only concerns (OQ-INIT.3). |
| Raw files | **Object storage (abstraction)** | Immutable raw copies (CC-2). Local filesystem in dev, S3-compatible (S3/MinIO) in prod. See ADR-006. Introduced in Phase 1. |
| Clean data | **`output_row` table in the backend DB (v1)** | Model-ready structured output. Dedicated warehouse deferred until scale. See ADR-005. |
| AI | **Claude (Anthropic API)** | Mapping / labelling / structure / anomaly-explanation suggestions (Phase 5). Provider abstraction; env-injected creds; profile-only inputs. See ADR-008. |

**Layering (backend):** `api/` routers stay thin (no business logic) → services →
`models/` / `db/`. Pydantic v2 schemas (`schemas/`) are kept separate from ORM
models (`models/`). See [`../CODING_STANDARDS.md`](../CODING_STANDARDS.md).

---

## 2. Database Strategy

This is a **hard requirement**, not a preference. Read it before touching either
database.

### 2.1 Two independent databases

The system uses **two separate databases** that do **not** share storage:

1. **Backend database** — the platform's metadata and configuration store
   (tenants, files, sheets, profiles, mapping configs, rules, jobs, job events,
   validation flags, suggestions, and — until a dedicated warehouse is chosen —
   clean output). Accessed by the Python backend via **SQLAlchemy 2.0 + Alembic**.
   Configured by the environment variable **`BACKEND_DATABASE_URL`**.

2. **UI database** — the Next.js front-end's own store, accessed via **Prisma**.
   Configured by the environment variable **`DATABASE_URL`** (in `front-end/.env`).

**They never share a database.** The front-end does not read the backend's
database directly; it talks to the backend over the API. This keeps the two
deployables independently swappable and independently scalable.

### 2.2 SQLite now, Postgres later — by config change only

Each database is **SQLite in development** and **swappable to Postgres later**.
The swap MUST require **configuration changes only — not query rewrites**:

- **Backend:** change `BACKEND_DATABASE_URL` from a
  `sqlite:///…` URL to a `postgresql+psycopg://…` URL. Run Alembic migrations.
  No model or query code changes.
- **UI (Prisma):** change the datasource `provider` from `"sqlite"` to
  `"postgresql"` and point `DATABASE_URL` at Postgres, then regenerate the client
  and migrate.

### 2.3 How portability is enforced

The swap is only "config-only" if we never let a dialect leak into code. The
rules (from [`../CODING_STANDARDS.md`](../CODING_STANDARDS.md)):

- **Never hardcode a DB URL or dialect** — always read from env.
- **Dialect-agnostic SQLAlchemy types only:** `String`, `Integer`, `Numeric`,
  `Boolean`, `DateTime(timezone=True)`, `JSON`, `Uuid`. Avoid Postgres-only types
  (`JSONB`, `ARRAY`, native `ENUM`) in models until/unless we commit to Postgres.
- **Enums as `String`**, validated in the app layer (Python `enum` / Pydantic) —
  not native DB enums.
- **Primary keys** are `Uuid` (maps to CHAR on SQLite) or `String` UUIDs —
  consistent across dialects.
- **Timestamps** are always UTC, `DateTime(timezone=True)`.
- **Alembic** is configured with `render_as_batch=True` (so SQLite `ALTER`
  works) and a **`MetaData` naming convention** so every index/constraint is
  explicitly named — a prerequisite for portable migrations.
- **No raw SQL** unless dialect-neutral; if unavoidable, branch per dialect.
- **Prisma schema stays portable** — avoid Postgres-only native types until the swap.

### 2.4 Testing posture

Tests run on **SQLite** for speed. Before switching any environment to Postgres,
a **Postgres integration job MUST pass** in CI. CI on every PR runs `ruff`,
`mypy`, and `pytest` (SQLite); a Postgres integration job is added before releases.

---

## 3. Tenant Isolation

**Decision (OQ-0.1 resolved): row-level isolation.** Every domain table carries
`tenant_id` (CC-1), and no query may return cross-tenant data. This is scaffolded
from Phase 0 because it is **hard to reverse**. Schema/DB-per-tenant was
considered and rejected for v1 as too heavy to operate at many-tenant scale
(migrations × N, connection routing). See ADR-003.

---

## 4. Config-as-Data & Versioning

All mappings and transformations are stored as **versioned data**, not code
(CC-4, P0-5). Older versions are retained so every output row is traceable to the
`mapping_config_version` and `rule_set_version` that produced it (CC-3). See
[`data-model.md`](./data-model.md).

---

## 5. Architecture Decision Log

Append an entry when a decision is made, changed, or superseded.
Format: **ADR-NNN — Title — Status (Accepted / Proposed / Superseded) — Date — Context / Decision / Consequences.**

### ADR-001 — Two independent databases (backend + UI) — Accepted — 2026-07
- **Context:** The backend (Python/FastAPI) and the front-end (Next.js) both need
  persistence, but coupling them to one database would block independent swap and
  scaling.
- **Decision:** Use two separate databases — backend via SQLAlchemy
  (`BACKEND_DATABASE_URL`), UI via Prisma (`DATABASE_URL`). They never share
  storage; the front-end reaches backend data only via the API.
- **Consequences:** Each side swaps SQLite→Postgres independently by config. No
  shared-schema coupling. The front-end must not query the backend DB directly.

### ADR-002 — SQLite in dev, Postgres later, via env-var URL only — Accepted — 2026-07
- **Context:** We want fast local iteration now but a production-grade DB later,
  without a rewrite.
- **Decision:** Both databases default to SQLite and swap to Postgres by changing
  only the URL (and, for Prisma, the datasource `provider`). Portability is
  enforced with dialect-agnostic types, string-stored enums, UUID PKs, UTC
  timestamps, Alembic batch mode + a MetaData naming convention, and no
  dialect-specific raw SQL.
- **Consequences:** The swap is config-only. A Postgres integration job must pass
  before any environment moves to Postgres.

### ADR-003 — Row-level tenant isolation — Accepted — 2026-07
- **Context:** Tenant isolation is hard to reverse and must be scaffolded from
  Phase 0 (CC-1).
- **Decision (OQ-0.1 resolved):** Row-level isolation — `tenant_id` on every
  domain table, enforced in every query. Schema/DB-per-tenant was considered and
  rejected for v1 (heavier ops at many-tenant scale).
- **Consequences:** Every model and query carries `tenant_id` from the start;
  Phase 7 adds tenant-scoping tests to verify no cross-tenant access paths.

### ADR-004 — Opinionated rule engine with a sandboxed-expression escape hatch — Accepted — 2026-07
- **Context:** The transformation engine must be flexible (config, not hardcode)
  yet intuitive, with an escape hatch for the ~10% of cases the fixed library
  doesn't cover.
- **Decision (OQ-3.1 resolved):** A fixed library of well-designed operations
  plus a `custom` rule whose payload is a **sandboxed expression language** — a
  restricted DSL evaluated over the row/field context. **No** arbitrary Python,
  imports, or I/O; allowlisted operators/functions only; resource-bounded
  (time/memory) evaluation.
- **Consequences:** More expressive than named-handler-only, but the sandbox is
  security-critical: the expression evaluator must be built with a strict
  allowlist and hard resource limits, and covered by adversarial tests. The exact
  grammar/function set is finalised in Phase 3.

### ADR-005 — Clean output = a backend-DB table for v1 — Accepted — 2026-07
- **Context:** The pipeline must land clean, model-ready rows somewhere. A
  dedicated analytics warehouse is more infrastructure than the MVP needs.
- **Decision (OQ-0.2 / OQ-INIT.2 resolved):** For v1, clean output is an
  `output_row` table in the **backend database** (SQLite→Postgres), carrying full
  traceability metadata (CC-3). A dedicated warehouse (e.g. BigQuery/Snowflake/
  Postgres-DW) is deferred until scale or analytics needs demand it.
- **Consequences:** No extra infra now; portability rules apply to `output_row`
  like any other table. Revisit when output volume or query patterns outgrow the
  operational DB.

### ADR-006 — Object storage abstraction (local dev / S3-compatible prod) — Accepted — 2026-07
- **Context:** Raw uploads must be stored immutably (CC-2) from Phase 1, without
  forcing a cloud dependency for local development.
- **Decision (OQ-INIT.1 resolved):** Introduce a storage abstraction with two
  backends selected by env: **local filesystem** in dev and **S3-compatible**
  (AWS S3 / MinIO) in prod. Callers depend on the abstraction, never a concrete
  SDK.
- **Consequences:** Dev needs no cloud credentials. Swapping/adding a backend is
  localized behind the interface. Provider-specific settings live in env only.

### ADR-007 — Async queue = Celery + Redis — Accepted — 2026-07
- **Context:** Batch processing (50–60 files/customer) can't run inline; Phase 7
  needs a queue with retries and per-tenant fairness.
- **Decision (OQ-7.1 resolved):** **Celery** with **Redis** as broker + result
  backend; autoscaling workers; per-tenant rate limiting/fairness. RQ was
  considered (simpler) but rejected as less flexible for fairness/rate-limiting
  at scale.
- **Consequences:** A Redis dependency is added in Phase 7. Jobs must remain
  idempotent (CC-6) so retries don't duplicate output.

### ADR-008 — AI provider = Claude via the Anthropic API — Accepted (cost ceiling deferred) — 2026-07
- **Context:** The suggestion layer (Phase 5) needs an LLM; provider and
  credential handling must be pinned, and inputs kept privacy-preserving.
- **Decision (OQ-5.1 / OQ-INIT.4):** Provider = **Claude via the Anthropic API**
  (most-capable model), behind a provider abstraction so the model is swappable.
  Credentials via env (`ANTHROPIC_API_KEY`), never in code. Only **profile data**
  (distinct values + column stats) is sent to the model, never raw row dumps
  (P5-1). **Open:** the per-file cost ceiling (OQ-5.1) — set once real usage data
  exists.
- **Consequences:** No secrets in the repo; the model choice is isolated behind
  the abstraction. Confidence calibration (OQ-5.2) remains deferred pending
  labelled accept/reject data.

### ADR-009 — Design system = extracted tokens + hand-built primitives — Accepted — 2026-07
- **Context:** The Review UI (Phase 6) needs a consistent design language without
  adopting a heavy third-party component library.
- **Decision (OQ-6.1 resolved):** Use the design tokens extracted from the
  reference UI (documented in `../front-end/CLAUDE.md`) plus **hand-built,
  shadcn-style primitives** (Card, Badge, Table, PageHeader, StatCard). No heavy
  component-library dependency.
- **Consequences:** Full control over styling and bundle size; all new UI must
  match the documented tokens. A component library can still be layered later if
  needed (revisit under OQ-6.1).

---

_Living document — update the stack, database strategy, and decision log as the
project evolves._
