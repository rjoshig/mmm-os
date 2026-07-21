"""FastAPI application entry point.

This Phase-0 scaffold exposes only a health route so the app boots and can be
wired into CI/dev. Feature routers (ingestion, mapping, transform, validation,
AI) are added thinly in their respective phases — routers hold no business logic.
"""

from __future__ import annotations

from fastapi import FastAPI

from mmm_os.core.config import get_settings
from mmm_os.core.logging import configure_logging


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

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

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Liveness probe.

        Returns:
            A small status payload including the active environment.
        """
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
