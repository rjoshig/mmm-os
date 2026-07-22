"""Object storage abstraction for immutable raw files (ADR-006, CC-2).

Local filesystem in dev, S3-compatible in prod, selected by env. Callers depend
on the ``ObjectStorage`` interface, never a concrete backend.
"""

from mmm_os.storage.base import (
    FileTooLargeError,
    ObjectAlreadyExistsError,
    ObjectStorage,
    StorageError,
    StoredObject,
)
from mmm_os.storage.factory import build_storage
from mmm_os.storage.local import LocalObjectStorage

__all__ = [
    "FileTooLargeError",
    "LocalObjectStorage",
    "ObjectAlreadyExistsError",
    "ObjectStorage",
    "StorageError",
    "StoredObject",
    "build_storage",
]
