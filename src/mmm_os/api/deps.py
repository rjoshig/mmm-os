"""FastAPI dependencies shared across routers.

These are thin providers (DB session, object storage) that routes depend on and
that tests override via ``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, status

from mmm_os.ai import LLMClient, LLMError, build_llm_client, load_llm_config
from mmm_os.canonical import CanonicalConfig, load_and_validate
from mmm_os.core.config import get_settings
from mmm_os.storage import ObjectStorage, build_storage


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


def get_llm_client() -> LLMClient:
    """Return an LLM client, or 503 if the LLM is disabled/unavailable.

    The LLM is off by default (ADR-008); enable it via config/env. Tests override
    this dependency with a fake client.

    Returns:
        A configured ``LLMClient``.

    Raises:
        HTTPException: 503 if the LLM is disabled or its SDK/config is unavailable.
    """
    try:
        return build_llm_client(load_llm_config())
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
