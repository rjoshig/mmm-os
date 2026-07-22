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
| Data sources | **`SourceConnector` abstraction** | Uploads/SFTP (file sources) + partner API connectors (Meta/Google Ads/DV360/TikTok) converge on one `LandedDataset` (CC-9). `FileSource` real now; connectors deferred to Phase 9. See ADR-010. |

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

## 5. Data Sources & Connectors

The platform ingests customer data from **multiple inbound sources** that all
converge into **one** pipeline: onboarding/staging → mapping (Phase 2) →
transform (Phase 3) → validation (Phase 4) → clean canonical "stack"/output. The
source layer makes that convergence explicit so connectors attach without a
refactor (CC-9). Connector *implementation* is deferred to
[Phase 9](./phases/phase-09-future-connectors-extraction.md); the **abstraction
is designed in now**.

### 5.1 The ingestion source abstraction

Every source implements a common **`SourceConnector`** contract
(`src/mmm_os/sources/base.py`):

- **`fetch(request) -> LandedDataset`** — produce the common landed representation.
- **`test_connection() -> bool`** — whether the source is reachable/authorised
  (trivially true for file sources; a live credential probe for API sources).
- **`list_available() -> list[...]`** — selectable entities (ad accounts, metrics,
  reports); empty for file sources.

Both source families emit the **same** `LandedDataset` (`sources/landed.py`),
tagged with `source_type` (`upload` / `sftp` / `api_connector`) and a `source_ref`
for traceability (CC-3). Nothing downstream depends on which connector produced it.

- **File sources** (upload today via `FileSource`; SFTP later) fetch/receive
  files and flow them through the existing Phase-1 parsing + structure detection
  to land one table per non-empty sheet (header row + inferred column structure).
  **`FileSource` is the first real implementation** and is what `ingestion`
  already routes through.
- **API sources** (partner connectors — Meta, Google Ads, DV360, TikTok) call the
  partner reporting API and normalise the response **directly** into landed
  records — no header detection needed, since partner report schemas are known
  and stable.

### 5.2 Partner connectors (API sources)

Connectors pull **each customer's own aggregate paid-media performance** (spend,
impressions, clicks, conversions, reach — by date/campaign/geo/placement) from
their authorised ad accounts. This is customer-specific **aggregate** reporting
data only — **no user-level PII**.

- **Auth & credentials (CC-10):** OAuth2 per customer per partner, plus support
  for long-lived/system-user tokens where a partner uses Business-Manager-style
  access. Tokens are stored **encrypted, tenant-scoped, least-privilege
  (read-only reporting scopes)**, auto-refreshed, with graceful handling of
  expiry/revocation surfaced as clear errors. **Tokens are never logged.**
- **Per-customer connector config:** account IDs, entities/metrics/dimensions to
  pull, currency, timezone, incremental lookback window, backfill range, schedule.
- **Scheduling/orchestration:** async workers (Phase-7 Celery+Redis, ADR-007) run
  scheduled syncs; incremental pulls use a **rolling lookback window** to catch
  partner-side restatements; backfill covers history; per-partner rate limiting,
  pagination, and retry/backoff. **Re-pulling a window replaces, never duplicates**
  (idempotent, CC-6).
- **Default mapping/taxonomy templates:** because partner schemas are stable, each
  connector ships **default column→canonical mappings and taxonomy defaults**
  (e.g. Meta `spend` → canonical `spend`; platform → `Facebook`), so partner data
  auto-maps with minimal human review — reusing the **Phase-2 template layer**,
  still human-ratifiable (CC-5).
- **Privacy:** aggregate reporting data only; requested scopes are documented per
  partner and kept least-privilege.

### 5.3 Glossary (external terms → our components)

A reader coming from other data platforms may use different names for the same
stages. This maps them onto our vocabulary:

| You may hear… | In `mmm-os` it is… |
|---|---|
| "staging / onboarding validation" | the **ingestion + structure-detection** stage (Phase 1) landing a `LandedDataset`, before mapping |
| "ETL cleansing / exception validation" | the **transform (Phase 3) + validation/anomaly (Phase 4)** phases |
| "stack data" / "the stack" | the clean, canonical, model-ready **output** (`output_row`, ADR-005) |
| "source / feed / integration" | a **`SourceConnector`** (upload, SFTP, or a partner API connector) |
| "landed / staged dataset" | the common **`LandedDataset`** every source emits |

---

## 6. Enterprise Readiness

These cross-cutting concerns each have a dedicated phase spec; summaries here point
to them. They extend — not replace — the two-DB strategy and portability rules.

### 6.1 Authentication & Identity (Phase 00.5, CC-11)

Application-level identity: tenant-scoped users, email/password + MFA, and SSO via
**OIDC/SAML** (pluggable per-tenant IdP). Every API endpoint requires
authenticated + authorized access (deny by default); the authorization hook
consumes the Phase-8 RBAC roles. Session/token store follows the portability rules
(SQLite now → Postgres by config). Distinct from partner-connector credentials
(Phase 9). See [`phases/phase-00.5-authentication-identity.md`](./phases/phase-00.5-authentication-identity.md).

### 6.2 Secrets Management (Phase 00.6, CC-12)

A single `SecretStore` abstraction for **all** sensitive material — app/signing
keys, auth/IdP secrets, partner OAuth tokens (CC-10), DB creds. Local
encrypted-dev backend now; pluggable KMS/vault later. The DB stores only a
`secret_ref` (pointer + metadata), never the value; secrets are never logged. See
[`phases/phase-00.6-secrets-management.md`](./phases/phase-00.6-secrets-management.md).

### 6.3 LLM Cost Controls (Phase 05.1, CC-13)

Per-tenant token/call **metering** (`llm_usage`), configurable **budgets/caps**
with enforcement (throttle/block at limit), plus cost reduction — profile-only
inputs (already CC in Phase 5), response caching, batching, and model-tier
routing. Resolves the deferred OQ-5.1 cost ceiling. See
[`phases/phase-05.1-llm-cost-controls.md`](./phases/phase-05.1-llm-cost-controls.md).

### 6.4 Observability & Monitoring (Phase 07.1, CC-7)

The platform-wide standard: structured logging with `tenant_id`/`job_id` context,
metrics (throughput/latency/failures/queue depth), tracing across API→worker,
alerting, dashboards, the `job_event` timeline, and per-connector sync health. The
standard is defined in Phase 07.1 but **instrumented incrementally from Phase 1**.
See [`phases/phase-07.1-observability-monitoring.md`](./phases/phase-07.1-observability-monitoring.md).

### 6.5 Resilience & Error Handling (Phase 07.2, CC-6)

Retry-with-backoff, a **dead-letter queue** for poison jobs, idempotency hardening
(retries never duplicate output), partner-API rate-limit/backoff with
partial-failure isolation, and circuit-breaker/graceful degradation. See
[`phases/phase-07.2-resilience-error-handling.md`](./phases/phase-07.2-resilience-error-handling.md).

### 6.6 Compliance Controls (Phase 08.1)

The SOC 2-aligned **technical controls** — complete audit logging, enforced
encryption in transit/at rest, access reviews, change-management traceability,
least-privilege verification, secrets via Phase 00.6. **Certification is an
organizational process, not a build artifact**; this phase delivers the controls
that make it achievable. Cross-references Phase 8 (governance) and Phase 10
(policy). See [`phases/phase-08.1-compliance-controls.md`](./phases/phase-08.1-compliance-controls.md).

### 6.7 Design-only tail (Phases 10–12)

Data governance & retention (10), deployment & infrastructure (11), and load/scale
testing (12) are **documented but not scheduled to build**. **Postgres migration
remains Deferred** — portability is already designed (§2), so it needs no new work.

---

## 7. Architecture Decision Log

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

### ADR-008 — AI provider = config-driven, dual OpenAI + Anthropic, off by default — Accepted (cost ceiling deferred) — 2026-07 (rev 2)
- **Context:** The suggestion layer (Phase 5) needs an LLM. It must support **both
  the OpenAI API format and the Anthropic SDK**, and switching between them (or
  changing the model) must be a **config/env change only** — no code edits. LLM
  calls must be **off by default** and explicitly enabled.
- **Decision (OQ-5.1 / OQ-INIT.4, revised):** A provider-agnostic `LLMClient`
  abstraction with two backends — **OpenAI** (`openai` SDK, also covers
  OpenAI-compatible endpoints via `base_url`) and **Anthropic** (`anthropic` SDK).
  Configuration comes from **env vars or an optional JSON config file**
  (`LLM_CONFIG_FILE`), with env overriding JSON. Key settings: `enabled` (default
  **false**), `provider` (`auto` | `openai` | `anthropic`), `model`, `api_key`
  (or `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`), `base_url`, thresholds. When
  `provider = auto`, the provider is **inferred from the model name** (`gpt*`/`o*`
  → OpenAI, `claude*` → Anthropic), so flipping providers can be as simple as
  changing the model. The SDKs are **optional dependencies** (`mmm-os[llm]`),
  imported lazily; the core runs without them. Only **profile data** (distinct
  values + column stats) is ever sent to the model, never raw row dumps (P5-1).
  **Open:** the per-file cost ceiling (OQ-5.1).
- **Consequences:** No secrets in the repo; provider/model are swappable by config
  alone; the LLM is inert unless explicitly enabled. Handlers depend on the
  `LLMClient` interface, so tests inject a fake with no network/SDK. Confidence
  calibration (OQ-5.2) remains deferred pending labelled accept/reject data.

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

### ADR-010 — Source-agnostic ingestion abstraction — Accepted — 2026-07
- **Context:** Customer data arrives from multiple inbound sources (uploads, SFTP
  drops, and partner ad-platform reporting APIs — Meta, Google Ads, DV360,
  TikTok), but all of it must feed the **same** mapping→transform→validation→output
  pipeline. Bolting connectors on later would force a refactor of everything
  downstream.
- **Decision:** Introduce a `SourceConnector` contract
  (`test_connection` / `list_available` / `fetch`) that every source implements,
  producing one common `LandedDataset` tagged with `source_type` + `source_ref`.
  Downstream phases consume the landed representation and never branch on source
  (CC-9). **Uploads are the first real implementation (`FileSource`), reusing the
  existing Phase-1 parsing/structure detection**; SFTP and API connectors are
  designed but deferred to Phase 9. New source/connector data-model entities
  (`source`, `connector`, `connector_config`, `connector_credential`, `sync_run`)
  are **documented now, not yet ORM-modelled**, so migrations stay clean until
  Phase 9 builds them.
- **Consequences:** Connectors attach at a single, stable seam. Credentials get a
  dedicated, encrypted, tenant-scoped, never-logged store (CC-10). Idempotent
  re-pulls (CC-6) and traceability to `source`/`sync_run` (CC-3) extend the
  existing invariants rather than replacing them. Two-DB strategy and all prior
  ADRs are untouched.

---

_Living document — update the stack, database strategy, and decision log as the
project evolves._
