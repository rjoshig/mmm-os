"""FastAPI dependencies shared across routers.

These are thin providers (DB session, object storage) that routes depend on and
that tests override via ``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache

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
