"""Select and build the object-storage backend from settings (ADR-006)."""

from __future__ import annotations

from mmm_os.core.config import Settings
from mmm_os.storage.base import ObjectStorage
from mmm_os.storage.local import LocalObjectStorage


def build_storage(settings: Settings) -> ObjectStorage:
    """Build the configured object-storage backend.

    Args:
        settings: Application settings (``storage_backend`` selects the backend).

    Returns:
        An ``ObjectStorage`` instance.

    Raises:
        NotImplementedError: If the configured backend is not available yet
            (the S3-compatible backend lands with the first prod deploy).
    """
    backend = settings.storage_backend.lower()
    if backend == "local":
        return LocalObjectStorage(settings.storage_local_path)
    raise NotImplementedError(
        f"storage backend {backend!r} is not implemented yet (S3-compatible backend "
        "lands with prod deploy; see ADR-006)"
    )
