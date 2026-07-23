"""Application configuration and settings.

Settings are read from the environment (and an optional local ``.env`` file).
No secrets or database URLs are hardcoded — see ``CODING_STANDARDS.md`` and
``docs/architecture.md`` (Database Strategy).
"""

from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate os.environ from .env so modules that read env vars directly (e.g.
# mmm_os.ai.config, which is not a pydantic-settings model) see them too —
# pydantic-settings' own env_file loading only feeds this Settings class.
load_dotenv()


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

    # Path-based ingestion (Phase 01.4): comma-separated ABSOLUTE directories the
    # backend may read files from by path (a "landing zone"), so large files are
    # ingested by reference instead of a browser upload. Empty = feature disabled.
    # Every ingest-by-path request is validated to sit within one of these roots
    # (canonicalized, no traversal) — nothing outside a configured root is reachable.
    ingest_landing_roots: str = ""

    # Secrets management (Phase 00.6, CC-12). "local" encrypts secrets on disk under
    # a key derived from secret_master_key; production swaps to a KMS/vault backend.
    secrets_backend: str = "local"
    secrets_local_path: str = "./_secrets"
    # Dev-only default key material; MUST be overridden via env in any real
    # deployment (never commit a real key). Used only by the local backend.
    secret_master_key: str = "dev-insecure-master-key-change-me"

    # LLM cost controls (Phase 05.1, CC-13). Per-tenant daily caps (0 = unlimited);
    # a per-tenant llm_budget row overrides these. Response caching reduces spend.
    llm_tenant_daily_token_cap: int = 0
    llm_tenant_daily_call_cap: int = 0
    llm_cache_enabled: bool = True

    # Authentication (Phase 00.5, CC-11). When enabled, feature endpoints require a
    # valid session. Defaults off so the API/tests run unauthenticated in dev; the
    # Review UI enables it. Session lifetime is in hours.
    auth_enabled: bool = False
    session_ttl_hours: int = 12
    # Seed a default admin on startup (dev convenience). Credentials below.
    seed_default_admin: bool = True
    default_admin_email: str = "admin"
    default_admin_password: str = "admin123"
    default_tenant_slug: str = "default"

    @property
    def cors_origins(self) -> list[str]:
        """Parse ``cors_allow_origins`` into a list of trimmed origins."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def landing_roots(self) -> list[str]:
        """Parse ``ingest_landing_roots`` into a list of trimmed absolute directories."""
        return [r.strip() for r in self.ingest_landing_roots.split(",") if r.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Returns:
        The process-wide settings, read once from the environment.
    """
    return Settings()
