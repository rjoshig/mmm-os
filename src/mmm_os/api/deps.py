"""FastAPI dependencies shared across routers.

These are thin providers (DB session, object storage) that routes depend on and
that tests override via ``app.dependency_overrides``.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from mmm_os.ai import LLMClient, LLMError, build_llm_client, load_llm_config
from mmm_os.ai.metering import MeteringLLMClient
from mmm_os.auth.service import Principal, resolve_session
from mmm_os.canonical import CanonicalConfig, load_and_validate
from mmm_os.core.config import get_settings
from mmm_os.db.session import get_session
from mmm_os.secrets import SecretStore, get_secret_store
from mmm_os.storage import ObjectStorage, build_storage


def get_secret_store_dep() -> SecretStore:
    """Return the process-wide secret store (overridable in tests)."""
    return get_secret_store()


def _principal_from_header(
    authorization: str | None, session: Session, store: SecretStore
) -> Principal | None:
    """Resolve a Bearer token to a Principal, or ``None`` if missing/invalid."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization[len("bearer ") :].strip()
    return resolve_session(session, store, token=token)


def require_auth(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
    store: SecretStore = Depends(get_secret_store_dep),
) -> Principal | None:
    """Enforce authenticated access on feature endpoints (CC-11).

    When ``auth_enabled`` is false (dev/tests default), requests pass through
    anonymously. When enabled, a valid session Bearer token is required, else 401.
    """
    if not get_settings().auth_enabled:
        return None
    principal = _principal_from_header(authorization, session, store)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


@lru_cache
def _cached_storage() -> ObjectStorage:
    return build_storage(get_settings())


def get_storage() -> ObjectStorage:
    """Return the process-wide object-storage backend.

    Returns:
        The configured ``ObjectStorage`` instance.
    """
    return _cached_storage()


@lru_cache
def _cached_canonical() -> CanonicalConfig:
    return load_and_validate()


def get_canonical() -> CanonicalConfig:
    """Return the process-wide validated canonical schema + taxonomies.

    Returns:
        The loaded ``CanonicalConfig``.
    """
    return _cached_canonical()


def get_llm_client(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> LLMClient:
    """Return a tenant-metered LLM client, or 503 if the LLM is disabled.

    The LLM is off by default (ADR-008); enable it via config/env. The returned
    client is wrapped with per-tenant metering + budget enforcement + caching
    (Phase 05.1, CC-13). Tests override this dependency with a fake client.

    Returns:
        A configured, metered ``LLMClient``.

    Raises:
        HTTPException: 503 if the LLM is disabled or its SDK/config is unavailable.
    """
    config = load_llm_config()
    try:
        inner = build_llm_client(config)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return MeteringLLMClient(
        inner,
        session=session,
        tenant_id=tenant_id,
        model=config.model,
        settings=get_settings(),
    )
