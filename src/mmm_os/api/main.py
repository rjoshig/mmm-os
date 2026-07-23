"""FastAPI application entry point.

This Phase-0 scaffold exposes only a health route so the app boots and can be
wired into CI/dev. Feature routers (ingestion, mapping, transform, validation,
AI) are added thinly in their respective phases — routers hold no business logic.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mmm_os.ai.errors import LLMBudgetExceededError
from mmm_os.api.deps import require_auth
from mmm_os.api.routers import (
    ai,
    auth,
    collaboration,
    configs,
    connectors,
    customers,
    files,
    governance,
    mapping,
    output,
    pipeline,
    reads,
    transform,
    validation,
)
from mmm_os.api.routers import (
    settings as settings_router,
)
from mmm_os.canonical import load_and_validate
from mmm_os.core.config import Settings, get_settings
from mmm_os.core.logging import configure_logging

logger = logging.getLogger("mmm_os.api")

# Matches the tenant UUID in a tenant-scoped path, e.g. /api/v1/tenants/<uuid>/...
_TENANT_PATH = re.compile(r"/tenants/([0-9a-fA-F-]{36})(?:/|$)")


def _tenant_id_from_path(path: str) -> uuid.UUID | None:
    """Extract the tenant UUID from a tenant-scoped request path, if present."""
    match = _TENANT_PATH.search(path)
    if match is None:
        return None
    try:
        return uuid.UUID(match.group(1))
    except ValueError:
        return None


def _cors_headers_for(request: Request, settings: Settings) -> dict[str, str]:
    """Return CORS headers to reflect back to an allowed browser origin, if any.

    Starlette generates unhandled-500 responses in ``ServerErrorMiddleware``, which
    sits *outside* ``CORSMiddleware`` — so those error responses would otherwise
    carry no CORS headers, and the browser reports them as a network failure
    ("cannot reach the API") instead of surfacing the real server error. Reflecting
    the headers here keeps error responses readable by the Review UI.
    """
    origin = request.headers.get("origin")
    if not origin:
        return {}
    allowed = settings.cors_origins
    if origin in allowed or "*" in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Loads and validates the canonical schema + taxonomies at startup (P0.1-6);
    invalid config raises and prevents boot.

    Returns:
        The configured ``FastAPI`` instance.
    """
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="mmm-os",
        description="Marketing Data Ingestion & Transformation Platform (API).",
        version="0.0.0",
    )

    # Fail fast: the app must not boot with an invalid canonical schema/taxonomy.
    app.state.canonical = load_and_validate()

    # Allow the Review UI (Phase 6) to call the API from the browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _route_customer_db(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Route a tenant-scoped request to its customer's database (Slice 7.2).

        No-op unless multi-DB routing is enabled and the path is tenant-scoped for a
        silo customer; otherwise the request uses the shared pool engine. The routed
        engine is bound via a ContextVar that ``RoutingSession`` reads.
        """
        if not settings.multi_db_routing_enabled:
            return await call_next(request)
        tenant_id = _tenant_id_from_path(request.url.path)
        if tenant_id is None:
            return await call_next(request)

        from mmm_os.db.routing import resolve_engine_for_tenant, use_engine
        from mmm_os.db.session import PoolSessionLocal
        from mmm_os.secrets import get_secret_store

        target = None
        try:
            with PoolSessionLocal() as control:
                target = resolve_engine_for_tenant(
                    tenant_id, control_session=control, store=get_secret_store()
                )
        except Exception:  # noqa: BLE001 - routing failure falls back to the pool
            logger.exception("db routing failed for tenant %s", tenant_id)
        with use_engine(target):
            return await call_next(request)

    # Auth routes are the entry point and are NOT behind require_auth.
    app.include_router(auth.router)
    # Customer/workspace management is platform-level (its endpoints are admin-gated).
    app.include_router(customers.router)

    # Every feature router requires authenticated access (CC-11). The dependency
    # is a no-op when auth_enabled is false (dev/tests default).
    protected = [Depends(require_auth)]
    app.include_router(files.router, dependencies=protected)
    app.include_router(reads.router, dependencies=protected)
    app.include_router(mapping.router, dependencies=protected)
    app.include_router(transform.router, dependencies=protected)
    app.include_router(validation.router, dependencies=protected)
    app.include_router(output.router, dependencies=protected)
    app.include_router(pipeline.router, dependencies=protected)
    app.include_router(settings_router.router, dependencies=protected)
    app.include_router(configs.router, dependencies=protected)
    app.include_router(collaboration.router, dependencies=protected)
    app.include_router(ai.router, dependencies=protected)
    # Governance/admin routes gate on Permission.ADMIN per-route (require_auth is
    # applied within them via require_permission).
    app.include_router(governance.router, dependencies=protected)
    app.include_router(connectors.router, dependencies=protected)

    @app.exception_handler(LLMBudgetExceededError)
    def _budget_exceeded(_request: Request, exc: LLMBudgetExceededError) -> JSONResponse:
        """Map an over-budget LLM call to 429 Too Many Requests (CC-13)."""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": str(exc)}
        )

    @app.exception_handler(Exception)
    def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        """Return a JSON 500 that still carries CORS headers (see _cors_headers_for).

        Without this, an unhandled server error reaches the browser without CORS
        headers and the Review UI misreports it as "cannot reach the API". Logging
        here also keeps 500s diagnosable in the server log.
        """
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
            headers=_cors_headers_for(request, settings),
        )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Liveness probe.

        Returns:
            A small status payload including the active environment.
        """
        return {"status": "ok", "env": settings.app_env}

    @app.on_event("startup")
    def _seed_admin() -> None:
        """Seed the default tenant + admin when auth is enabled (dev convenience)."""
        if not (settings.auth_enabled and settings.seed_default_admin):
            return
        from mmm_os.auth.service import seed_default_admin
        from mmm_os.db.session import SessionLocal

        with SessionLocal() as db:
            try:
                seed_default_admin(db, settings)
                db.commit()
            except Exception:  # noqa: BLE001 - seeding must never block boot
                db.rollback()

    @app.on_event("startup")
    def _start_scheduler() -> None:
        """Start the in-app connector scheduler when enabled (Cycle 3, opt-in)."""
        if not settings.scheduler_enabled:
            return
        import threading

        def _loop() -> None:
            import time

            from mmm_os.connectors.autoschedule import run_due_syncs
            from mmm_os.db.session import SessionLocal
            from mmm_os.models.mixins import utcnow

            while True:
                time.sleep(max(5, settings.scheduler_poll_seconds))
                try:
                    with SessionLocal() as db:
                        run_due_syncs(db, utcnow())
                        db.commit()
                except Exception:  # noqa: BLE001 - a scheduler tick must not crash the loop
                    logger.exception("scheduler tick failed")

        threading.Thread(target=_loop, name="connector-scheduler", daemon=True).start()
        logger.info("connector scheduler started (every %ss)", settings.scheduler_poll_seconds)

    return app


app = create_app()
