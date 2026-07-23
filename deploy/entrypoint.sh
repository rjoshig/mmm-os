#!/usr/bin/env bash
# Container entrypoint (Phase 11). Applies DB migrations (idempotent) then starts
# the requested role. Config comes entirely from the environment (12-factor):
#   BACKEND_DATABASE_URL, SECRET_MASTER_KEY, AUTH_ENABLED, SCHEDULER_ENABLED, …
set -euo pipefail

ROLE="${1:-api}"

# The API host/port. Behind a proxy/ingress in real deployments.
HOST="${MMM_OS_HOST:-0.0.0.0}"
PORT="${MMM_OS_PORT:-8000}"
WORKERS="${MMM_OS_WORKERS:-2}"

run_migrations() {
  echo "[entrypoint] applying database migrations…"
  alembic upgrade head
}

case "$ROLE" in
  api)
    run_migrations
    echo "[entrypoint] starting API on ${HOST}:${PORT} (${WORKERS} workers)…"
    exec uvicorn mmm_os.api.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
    ;;
  migrate)
    # Run migrations only (e.g. a one-shot job before rolling out new app pods).
    run_migrations
    ;;
  *)
    # Escape hatch: run an arbitrary command inside the app environment.
    exec "$@"
    ;;
esac
