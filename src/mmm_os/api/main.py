"""FastAPI application entry point.

This Phase-0 scaffold exposes only a health route so the app boots and can be
wired into CI/dev. Feature routers (ingestion, mapping, transform, validation,
AI) are added thinly in their respective phases — routers hold no business logic.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mmm_os.ai.errors import LLMBudgetExceededError
from mmm_os.api.deps import require_auth
from mmm_os.api.routers import (
    ai,
    auth,
    connectors,
    files,
    governance,
    mapping,
    output,
    pipeline,
    reads,
    transform,
    validation,
)
from mmm_os.canonical import load_and_validate
from mmm_os.core.config import get_settings
from mmm_os.core.logging import configure_logging


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

    # Auth routes are the entry point and are NOT behind require_auth.
    app.include_router(auth.router)

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

    return app


app = create_app()
