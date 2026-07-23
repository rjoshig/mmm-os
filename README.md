# mmm-os

**Marketing Data Ingestion & Transformation Platform** (Mutinex DataOS–inspired).

A multi-tenant, config-driven platform that ingests messy marketing data files
(CSV / XLSX, including multi-tab workbooks), auto-detects their structure, maps
columns to a canonical schema, transforms and standardises them via a
declarative rule engine, validates for quality/anomalies, and outputs clean,
model-ready tabular data — with an **AI suggest-not-decide** layer and a
**human approve/reject** review loop. It is the *data provisioning layer*
upstream of Marketing Mix Modelling; **it is not the modelling engine.**

> **Status:** the core platform (Phases 0–9) plus the enterprise-readiness
> phases are built and green — file ingestion, structure detection, mapping,
> the transformation rule engine, validation/anomaly detection, the AI
> suggestion layer, the Next.js review UI, auth, secrets, async workers,
> observability, resilience, governance/RBAC, LLM cost controls, and partner
> connectors (full framework with mock partner clients). Spec-only phases 10–12,
> the Postgres migration, and PDF/email extraction remain deliberately deferred.
> [`docs/phases/README.md`](./docs/phases/README.md) is the authoritative status.

## Repository layout

```
mmm-os/
├── CLAUDE.md              # Guide for future sessions — read this first
├── CODING_STANDARDS.md    # Python + front-end + database standards
├── GIT_STANDARDS.md       # Branching, commits, PRs
├── docs/                  # PRD, build plan, schema, data model, architecture, phases
├── sampledata/            # Realistic sample marketing files for testing (see below)
├── src/mmm_os/            # Python backend (FastAPI, SQLAlchemy 2.0)
├── migrations/            # Alembic environment + versions
├── tests/                 # pytest suite
└── front-end/             # Next.js (App Router, TypeScript, Tailwind) review UI
```

## Tech stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy 2.0 + Alembic, provider-agnostic
  seams for object storage / task queue / secrets / LLM.
- **Front-end:** Next.js (React, TypeScript, App Router, Tailwind), Prisma.
- **Databases:** two independent databases (backend + UI), each SQLite now and
  swappable to Postgres via an environment-variable URL only. They do **not**
  share a database; the front-end talks to the backend via API.
- **Python dependency management:** `uv` (`pyproject.toml`).

## Prerequisites

- **Python 3.10+** and **[`uv`](https://docs.astral.sh/uv/)** (`pip install uv` or
  `curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Node.js 18+** and **npm** (only needed for the review UI).

---

## Quick start (backend API)

From the repo root:

```bash
# 1. Configure the environment (SQLite defaults work out of the box).
cp .env.example .env

# 2. Install dependencies into a local virtualenv.
uv sync

# 3. Create the database schema (runs cleanly on an empty SQLite base).
uv run alembic upgrade head

# 4. Boot the API with autoreload.
uv run uvicorn mmm_os.api.main:app --reload
```

The API is now at **http://localhost:8000**. Check it:

```bash
curl -s http://localhost:8000/health
# {"status":"ok","env":"development"}
```

Interactive API docs (every endpoint, try-it-out): **http://localhost:8000/docs**.

> **Auth is off by default** (`AUTH_ENABLED=false`) so you can drive the API
> directly in dev. Flip it on in `.env` to require login; the app then seeds a
> default admin (`admin` / `admin123`, configurable). The review UI always
> expects auth on — see below.

## Quick start (review UI)

In a second terminal, with the backend running:

```bash
cd front-end
cp .env.example .env             # NEXT_PUBLIC_API_BASE_URL defaults to :8000
npm install
npx prisma generate
npm run dev                      # http://localhost:3000
```

To use the UI end-to-end, enable auth on the backend so login works. Stop the API,
set `AUTH_ENABLED=true` in the **root** `.env`, restart `uvicorn`, then open
**http://localhost:3000** and sign in with `admin` / `admin123`. The admin console
(Users / Audit log / Access review) appears in the sidebar for admin users.

---

## Sample data

[`sampledata/`](./sampledata/) contains **15 realistic, deliberately messy**
marketing files (CSV + multi-tab XLSX, 100–200 rows each) — Meta/Google/TikTok
exports, video, programmatic, offline TV/radio/OOH, email, affiliate, retail
sales, and a blended "messy" export with channel aliases, mixed date formats,
currency symbols, blanks, and outliers. See
[`sampledata/README.md`](./sampledata/README.md) for the full catalogue and
suggested starter files.

They exist to exercise the whole pipeline: **structure detection → mapping →
transform → validation**. Regenerate them any time (byte-stable, fixed seed):

```bash
uv run python sampledata/generate_sample_data.py
```

---

## Testing it end-to-end

### Option A — the review UI (recommended)

With the backend (auth on) and UI both running:

1. **Sign in** at http://localhost:3000 (`admin` / `admin123`).
2. **Upload** a sample file — e.g. `sampledata/facebook_ads_2024.csv`. It is stored
   immutably and a processing job runs (structure detection + profiling).
3. **Open the file** to see the detected sheet(s), columns, and inferred types.
4. **Map columns** to the canonical schema on the mapping screen (try Auto-map,
   then adjust). For AI-assisted mapping, set an LLM key in `.env` (optional).
5. **Build transforms** — add declarative rules (e.g. standardise the `channel`
   value `FB` → `Facebook`) and watch the live before/after preview.
6. **Review validation** — quality checks and anomaly flags surface for
   approve/reject. Try `messy_mixed_export.csv` to see flags fire.

### Option B — the API directly (auth off)

With `AUTH_ENABLED=false` (the default), any UUID is a valid tenant id. This
walks a file through ingest → process → read structure → sample rows:

```bash
BASE=http://localhost:8000/api/v1
TENANT=11111111-1111-1111-1111-111111111111

# 1. Upload a sample file (stored immutably; returns the file + job).
FILE_ID=$(curl -s -X POST "$BASE/tenants/$TENANT/files" \
  -F "upload=@sampledata/facebook_ads_2024.csv" | python -c 'import sys,json;print(json.load(sys.stdin)["file"]["id"])')
echo "file: $FILE_ID"

# 2. Process it: detect structure + profile every sheet.
curl -s -X POST "$BASE/tenants/$TENANT/files/$FILE_ID/process" | python -m json.tool

# 3. List files (dashboard view: status, sheet + needs-review counts).
curl -s "$BASE/tenants/$TENANT/files" | python -m json.tool

# 4. Inspect the file's detected sheets + columns.
curl -s "$BASE/tenants/$TENANT/files/$FILE_ID" | python -m json.tool

# 5. Grab a SHEET_ID from step 4, then preview the first real data rows.
SHEET_ID=<paste-a-sheet-id-here>
curl -s "$BASE/tenants/$TENANT/sheets/$SHEET_ID/rows?limit=10" | python -m json.tool

# 6. Auto-map the sheet's columns to the canonical schema by signature.
curl -s -X POST "$BASE/tenants/$TENANT/sheets/$SHEET_ID/automap" | python -m json.tool

# 7. See the canonical target fields everything maps to.
curl -s "$BASE/canonical/fields" | python -m json.tool
```

Multi-tab workbooks (`multi_channel_workbook.xlsx`, `meta_multi_account.xlsx`)
come back as multiple sheets from step 4 — process and map each independently.
The full endpoint list is in the Swagger UI at `/docs`.

---

## Quality gates

Run these before committing (all must pass):

```bash
# Backend
uv run ruff check .            # lint
uv run ruff format --check .   # formatting
uv run mypy src                # types (strict)
uv run pytest                  # test suite

# Database migrations round-trip cleanly (no drift)
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```

```bash
# Front-end (from front-end/)
npm run lint
npm run typecheck
npm run build
npm run format:check
```

## Configuration reference

Backend settings are read from the environment (`.env`), documented in
[`.env.example`](./.env.example). The ones you're most likely to touch:

| Variable | Default | Purpose |
|---|---|---|
| `BACKEND_DATABASE_URL` | `sqlite:///./mmm_os.db` | Backend DB URL (swap to Postgres by URL only). |
| `AUTH_ENABLED` | `false` | Require authenticated, tenant-scoped access on every endpoint. |
| `SEED_DEFAULT_ADMIN` / `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` | `true` / `admin` / `admin123` | Seed a dev admin when auth is on. |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | Origins the review UI is served from. |
| LLM / cost-control keys | commented | Enable the AI suggestion layer + per-tenant budgets (optional). |

The front-end reads `NEXT_PUBLIC_API_BASE_URL` (`front-end/.env`), defaulting to
`http://localhost:8000`.

## Documentation

Start with **[`CLAUDE.md`](./CLAUDE.md)**, then see [`docs/`](./docs/):

- [`docs/prd.md`](./docs/prd.md) — product requirements.
- [`docs/build-plan.md`](./docs/build-plan.md) — phase roadmap + cross-cutting requirements.
- [`docs/canonical-schema.md`](./docs/canonical-schema.md) — canonical schema + taxonomies.
- [`docs/data-model.md`](./docs/data-model.md) — entities + rule schema.
- [`docs/architecture.md`](./docs/architecture.md) — stack, database strategy, decisions.
- [`docs/phases/README.md`](./docs/phases/README.md) — **authoritative** phase order + status.

## Contributing

Read [`CODING_STANDARDS.md`](./CODING_STANDARDS.md) and
[`GIT_STANDARDS.md`](./GIT_STANDARDS.md). Build phase-by-phase in order; do not
implement anything marked *Deferred* or *Out of scope*; resolve items in
[`docs/open-questions.md`](./docs/open-questions.md) before assuming.
