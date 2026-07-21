# Coding Standards — mmm-os

## General
- Python **3.10+**: code MUST run on 3.10. Do not use 3.11+-only syntax/stdlib.
- Front-end: TypeScript (strict), Next.js App Router.
- Every package/module has a docstring/README stating its single responsibility.
- Small, single-responsibility functions. Prefer pure functions in transform/ and validation/.
- No secrets in code — all configuration via environment variables.

## Python
- Dependency management: `uv` with `pyproject.toml`.
- Lint + format: `ruff` (format and lint). Type-check: `mypy` (as strict as practical).
- Tests: `pytest`. Phase acceptance criteria become test cases.
- Type hints required on all public functions. Google-style docstrings.
- FastAPI layering: `api/` routers (thin, no business logic) → services → `models/`/`db/`.
- Pydantic v2 schemas in `schemas/`, kept separate from ORM models in `models/`.
- Errors: raise typed exceptions in services; map to HTTP in the api layer; never leak stack traces to clients.
- Logging: structured (JSON-capable), no `print`. Include `tenant_id` and `job_id` in context where relevant.
- Naming: snake_case for functions/vars/modules, PascalCase for classes, UPPER_SNAKE for constants.

## Database — portability is a HARD requirement
- ORM: SQLAlchemy 2.0 (typed `DeclarativeBase`). Migrations: Alembic.
- **Two separate databases**, each behind its own env var, each SQLite now / Postgres later:
  - Backend (Python): `BACKEND_DATABASE_URL`.
  - UI (Next.js/Prisma): `DATABASE_URL`.
- Never hardcode a DB URL or dialect; always read from env.
- Write dialect-agnostic models: use generic SQLAlchemy types (`String`, `Integer`, `Numeric`, `Boolean`, `DateTime(timezone=True)`, `JSON`, `Uuid`). Avoid Postgres-only types (`JSONB`, `ARRAY`, native `ENUM`) in models until/unless we commit to Postgres.
- Enums: store as `String` and validate in the app layer (Python `enum` / Pydantic), not native DB enums.
- Primary keys: use `Uuid` (maps to CHAR on SQLite) or `String` UUIDs — consistent across dialects.
- Timestamps: always UTC; `DateTime(timezone=True)`.
- Alembic: set `render_as_batch=True` so SQLite `ALTER` works; apply a `MetaData` naming convention so all indexes/constraints are explicitly named (portable migrations).
- No raw SQL unless dialect-neutral; if unavoidable, branch per dialect.
- Tests run on SQLite for speed; a Postgres integration job MUST pass before switching any environment to Postgres.

## Front-end (Next.js)
- TypeScript strict; ESLint + Prettier.
- UI database via Prisma. To swap SQLite→Postgres later: change the datasource `provider` and `DATABASE_URL`, then regenerate/migrate. Keep the Prisma schema portable (avoid Postgres-only native types until the swap).
- Functional components + hooks. No business logic in components; data access via a thin client/API layer.
- All UI MUST match the reference design language documented in `front-end/CLAUDE.md`.

## Testing & CI
- Unit tests per module; integration tests for pipelines.
- CI on every PR: `ruff`, `mypy`, `pytest` (SQLite). Add a Postgres integration job before releases.
