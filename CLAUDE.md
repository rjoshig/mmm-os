# CLAUDE.md — mmm-os

Guide for Claude Code (and any future session) working in this repository.
**Read this first.**

## What this project is

`mmm-os` is a multi-tenant, config-driven **Marketing Data Ingestion &
Transformation Platform** (Mutinex DataOS–inspired). It ingests messy marketing
data files (CSV / XLSX, including multi-tab workbooks), auto-detects their
structure, maps columns to a **canonical schema**, transforms and standardises
them via a **declarative rule engine**, validates for quality and anomalies, and
outputs clean, model-ready tabular data — accelerated by an **AI suggest-not-decide**
layer and gated by a **human approve/reject** review loop. It is the data
provisioning layer *upstream* of Marketing Mix Modelling; it is **not** the
modelling engine.

## Repository layout

```
mmm-os/
├── CLAUDE.md                # This guide.
├── CODING_STANDARDS.md      # Python + front-end + database standards.
├── GIT_STANDARDS.md         # Branching, Conventional Commits, PRs.
├── README.md                # Human-facing overview + run instructions.
├── .env.example             # Backend environment template (BACKEND_DATABASE_URL).
├── pyproject.toml           # Python project (uv-managed) + tool config.
├── alembic.ini              # Alembic configuration.
├── docs/                    # All project documentation (see below).
├── src/mmm_os/              # Python backend package (placeholder subpackages).
│   ├── api/                 # FastAPI routers (thin). [Phase 1+]
│   ├── core/                # Config, settings, logging. [Phase 0]
│   ├── db/                  # SQLAlchemy engine, session, Base. [Phase 0]
│   ├── models/              # ORM models. [Phase 0]
│   ├── schemas/             # Pydantic v2 schemas. [Phase 0]
│   ├── ingestion/           # File ingestion + structure detection. [Phase 1]
│   ├── sources/             # Source-agnostic ingestion seam (FileSource → LandedDataset). [Phase 1; CC-9]
│   ├── connectors/          # Partner connectors (SFTP/Meta/Google Ads/DV360/TikTok). [Phase 9 — placeholders]
│   ├── mapping/             # Mapping engine + saved configs. [Phase 2]
│   ├── transform/           # Declarative transformation rule engine. [Phase 3]
│   ├── validation/          # Validation + anomaly detection. [Phase 4]
│   ├── ai/                  # AI suggestion layer. [Phase 5]
│   └── workers/             # Async background tasks. [Phase 7]
├── migrations/              # Alembic env + versions.
├── tests/                   # pytest suite.
└── front-end/               # Next.js UI shell (see front-end/CLAUDE.md). [Phase 6]
```

## Documentation map

Read the doc relevant to your task before writing code:

- [`docs/prd.md`](./docs/prd.md) — Product requirements: background, scope, capabilities, ETL flow, rule engine, AI layer, tech stack, risks.
- [`docs/build-plan.md`](./docs/build-plan.md) — High-level phase roadmap (0–9) + cross-cutting requirements CC-1…CC-10.
- [`docs/canonical-schema.md`](./docs/canonical-schema.md) — The canonical target schema (Appendix A) + standard taxonomies (Appendix B). The fixed contract everything resolves to.
- [`docs/data-model.md`](./docs/data-model.md) — Data-model entities (Appendix C, incl. C.1 source/connector entities) + declarative rule schema (Appendix D).
- [`docs/architecture.md`](./docs/architecture.md) — Tech stack, the two-database strategy, the **Data Sources & Connectors** abstraction (source-agnostic ingestion; §5), and the running architecture-decision log.
- [`docs/open-questions.md`](./docs/open-questions.md) — Consolidated open questions (Appendix E) + any surfaced since. **Resolve the relevant ones before assuming.**
- [`docs/phases/README.md`](./docs/phases/README.md) — Phase index, statuses, MVP definition, and the sub-phase naming convention.
- [`docs/phases/phase-NN-*.md`](./docs/phases/) — One spec per phase, each with Objective · Scope · Functional Requirements · Deliverables · Acceptance Criteria · Dependencies · Open Questions · Sub-phases.

**Before working on a phase:** read that phase's `docs/phases/phase-NN-*.md`
**and the phase(s) it depends on**. Do not start a phase until the prior phase's
acceptance criteria pass.

## Golden rules

1. **Build phase-by-phase, in order.** Follow `docs/phases/`. The MVP is Phases 0–4.
2. **Honor the cross-cutting requirements (CC-1…CC-10) in every phase:**
   - **Multi-tenant:** every persisted record carries `tenant_id`; no query returns cross-tenant data.
   - **Immutable raw files:** original uploads are stored unaltered; processing works on copies/derived data.
   - **Config-as-data:** all mappings and transformations are stored as versioned data, never as code.
   - **Human-in-the-loop AI:** AI never auto-commits; suggestions require human accept/reject/modify.
   - **Idempotent jobs:** re-running a job on the same input yields the same result, with no duplicate output.
   - **Traceability:** every output row traces to its source (file+sheet+row, or `source`/`sync_run`) + applied config/rule versions.
   - **Observability:** every job stage emits status + timing + error records.
   - **Source-agnostic pipeline (CC-9):** mapping/transform/validation/output operate on the common `LandedDataset` regardless of source; sources implement one `SourceConnector` contract (ADR-010).
   - **Credential security (CC-10):** partner credentials/tokens are encrypted at rest, tenant-scoped, least-privilege, and never logged.
3. **Never build anything marked Deferred / Out of scope** (e.g. Phase 9 connectors and PDF/email extraction) unless explicitly told.
4. **Resolve Open Questions before assuming.** If something is unspecified, add it to [`docs/open-questions.md`](./docs/open-questions.md) and ask — do not invent requirements.
5. **Database portability is a hard requirement.** Two independent databases (backend + UI), each SQLite now and swappable to Postgres via env-var URL only. Use dialect-agnostic types; read the URL from env; never hardcode a dialect. See [`docs/architecture.md`](./docs/architecture.md).

## Standards

- **Code:** follow [`CODING_STANDARDS.md`](./CODING_STANDARDS.md) (Python 3.10-safe, `uv`, `ruff`/`mypy`/`pytest`, SQLAlchemy 2.0 portability rules, TypeScript-strict front-end).
- **Git:** follow [`GIT_STANDARDS.md`](./GIT_STANDARDS.md) (branch prefixes, Conventional Commits, one-phase-per-PR with a linked phase + acceptance checklist, no secrets, `.env` never committed).
- **Front-end:** all UI must match the design language documented in [`front-end/CLAUDE.md`](./front-end/CLAUDE.md).
