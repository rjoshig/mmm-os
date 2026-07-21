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
| Workers | **Celery / RQ** | Async batch file processing (introduced in Phase 7). |
| Backend metadata + config DB | **SQLite now → Postgres later** | SQLAlchemy 2.0 + Alembic. Tenants, files, mappings, jobs, rules. |
| UI DB | **SQLite now → Postgres later** | Prisma. Separate from the backend DB. |
| Raw files | **Object storage (S3/GCS)** | Immutable raw copies (CC-2). Introduced in Phase 1. |
| Clean data | **Warehouse** | Model-ready structured output. Warehouse choice is OQ-0.2. |
| AI | **LLM** | Mapping / labelling / structure / anomaly-explanation suggestions (Phase 5). |

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

Recommended default (P0-4): **row-level isolation** — every domain table carries
`tenant_id` (CC-1), and no query may return cross-tenant data. This is scaffolded
from Phase 0 because it is **hard to reverse**. The final choice (row-level vs
schema/DB-per-tenant) is **OQ-0.1** and must be confirmed in Phase 0.

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

### ADR-003 — Row-level tenant isolation (default recommendation) — Proposed — 2026-07
- **Context:** Tenant isolation is hard to reverse and must be scaffolded from
  Phase 0 (CC-1).
- **Decision (proposed):** Default to row-level isolation — `tenant_id` on every
  domain table, enforced in every query. Final confirmation is **OQ-0.1** in
  Phase 0.
- **Consequences:** Every model and query carries `tenant_id` from the start. If
  schema/DB-per-tenant is later chosen instead, the change is significant — hence
  confirm early.

### ADR-004 — Opinionated rule engine with an escape hatch — Proposed — 2026-07
- **Context:** The transformation engine must be flexible (config, not hardcode)
  yet intuitive.
- **Decision (proposed):** A fixed library of well-designed operations covering
  ~90% of cases, plus a `custom` escape-hatch rule for the rest. Scope of the
  escape hatch is **OQ-3.1**.
- **Consequences:** Keeps the UI intuitive and AI suggestions sharp. The escape
  hatch's exact power (expression language? sandboxed code? none for v1?) is
  deferred to Phase 3.

---

_Living document — update the stack, database strategy, and decision log as the
project evolves._
