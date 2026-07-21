# mmm-os

**Marketing Data Ingestion & Transformation Platform** (Mutinex DataOS–inspired).

A multi-tenant, config-driven platform that ingests messy marketing data files
(CSV / XLSX, including multi-tab workbooks), auto-detects their structure, maps
columns to a canonical schema, transforms and standardises them via a
declarative rule engine, validates for quality/anomalies, and outputs clean,
model-ready tabular data — with an **AI suggest-not-decide** layer and a
**human approve/reject** review loop. It is the *data provisioning layer*
upstream of Marketing Mix Modelling; **it is not the modelling engine.**

> **Status:** repository initialization — scaffolding + documentation only.
> No ingestion / mapping / transformation / validation / AI logic is implemented
> yet. Build proceeds strictly phase-by-phase per `docs/phases/`.

## Repository layout

```
mmm-os/
├── CLAUDE.md              # Guide for future sessions — read this first
├── CODING_STANDARDS.md    # Python + front-end + database standards
├── GIT_STANDARDS.md       # Branching, commits, PRs
├── docs/                  # PRD, build plan, schema, data model, architecture, phases
├── src/mmm_os/            # Python backend (FastAPI, SQLAlchemy 2.0) — placeholder packages
├── migrations/            # Alembic environment + versions
├── tests/                 # pytest suite
└── front-end/             # Next.js (App Router, TypeScript, Tailwind) UI shell
```

## Documentation

Start with **[`CLAUDE.md`](./CLAUDE.md)**, then see [`docs/`](./docs/):

- [`docs/prd.md`](./docs/prd.md) — product requirements.
- [`docs/build-plan.md`](./docs/build-plan.md) — phase roadmap + cross-cutting requirements.
- [`docs/canonical-schema.md`](./docs/canonical-schema.md) — canonical schema + taxonomies.
- [`docs/data-model.md`](./docs/data-model.md) — entities + rule schema.
- [`docs/architecture.md`](./docs/architecture.md) — stack, database strategy, decisions.
- [`docs/open-questions.md`](./docs/open-questions.md) — unresolved decisions.
- [`docs/phases/`](./docs/phases/) — one spec per phase (0–9). MVP = Phases 0–4.

## Tech stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy 2.0 + Alembic, Celery/RQ workers (later), LLM for suggestions.
- **Front-end:** Next.js (React, TypeScript, App Router, Tailwind), Prisma.
- **Databases:** two independent databases (backend + UI), each SQLite now and
  swappable to Postgres via an environment-variable URL only. They do **not**
  share a database; the front-end talks to the backend via API.
- **Python dependency management:** `uv` (`pyproject.toml`).

## Local development

### Backend

```bash
cp .env.example .env            # then edit as needed
uv sync                         # install dependencies
uv run alembic upgrade head     # runs cleanly on an empty SQLite base
uv run uvicorn mmm_os.api.main:app --reload   # boots the API (health route)
```

Quality gates:

```bash
uv run ruff check .
uv run mypy src
uv run pytest
```

### Front-end

```bash
cd front-end
cp .env.example .env            # then edit as needed
npm install
npx prisma generate
npm run dev                     # http://localhost:3000
```

Quality gates:

```bash
npm run lint
npm run typecheck
npm run build
```

## Contributing

Read [`CODING_STANDARDS.md`](./CODING_STANDARDS.md) and
[`GIT_STANDARDS.md`](./GIT_STANDARDS.md). Build phase-by-phase in order; do not
implement anything marked *Deferred* or *Out of scope*; resolve items in
[`docs/open-questions.md`](./docs/open-questions.md) before assuming.
