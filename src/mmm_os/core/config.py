"""Application configuration and settings.

Settings are read from the environment (and an optional local ``.env`` file).
No secrets or database URLs are hardcoded — see ``CODING_STANDARDS.md`` and
``docs/architecture.md`` (Database Strategy).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend application settings, populated from environment variables.

    Attributes:
        app_env: Deployment environment name (development/staging/production).
        log_level: Logging verbosity (DEBUG/INFO/WARNING/ERROR).
        backend_database_url: SQLAlchemy URL for the BACKEND database. Defaults to
            a local SQLite file for development; swap to Postgres by changing only
            this value (portability is a hard requirement).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    log_level: str = "INFO"

    # The BACKEND database (SQLAlchemy). The UI (Prisma) database is configured
    # separately in front-end/.env via DATABASE_URL — they never share storage.
    backend_database_url: str = "sqlite:///./mmm_os.db"

    # Object storage for immutable raw files (ADR-006). Backend is selected by
    # env: "local" (dev) writes under storage_local_path; "s3" is the prod target.
    storage_backend: str = "local"
    storage_local_path: str = "./_storage"

    # Max accepted upload size in bytes (OQ-1.1). Default ~200 MB.
    max_upload_bytes: int = 200 * 1024 * 1024

    # Structure detection: rows previewed per sheet for header/type detection.
    structure_preview_rows: int = 1000

    # Profiling bounds (01.3): capped distinct values and sample size per column.
    profile_distinct_limit: int = 1000
    profile_sample_limit: int = 20

    # CORS: comma-separated origins allowed to call the API (the Review UI, Phase 6).
    # Dev default is the Next.js dev server; tighten per environment.
    cors_allow_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        """Parse ``cors_allow_origins`` into a list of trimmed origins."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Returns:
        The process-wide settings, read once from the environment.
    """
    return Settings()
