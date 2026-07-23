# syntax=docker/dockerfile:1
# Backend API + worker image (Phase 11). Runs the FastAPI app under uvicorn; the
# same image runs migrations at start and can run the connector scheduler in-process
# (SCHEDULER_ENABLED=true). Database + secrets are injected via env at deploy time
# (CC-12) — never baked into the image.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# uv provides fast, reproducible installs from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (cached) from the lockfile, including the Postgres
# driver — production targets Postgres via BACKEND_DATABASE_URL.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --extra postgres

# Then the application source + migrations.
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra postgres

COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# entrypoint applies migrations (idempotent) then starts the API; override CMD for
# a worker-only role if/when workers move out of process.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["api"]
