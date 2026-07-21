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


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Returns:
        The process-wide settings, read once from the environment.
    """
    return Settings()
