"""Object-storage interface and value types.

Storage is content-agnostic and **immutable** (CC-2): a key is written once and
never overwritten. Writes are streamed in chunks so large files never load fully
into memory (P1-6), computing size + SHA-256 as they go.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import IO

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB


@dataclass(frozen=True)
class StoredObject:
    """Metadata describing a stored object.

    Attributes:
        key: The storage key the object was written to.
        uri: A backend-specific URI locating the object.
        size: The object's size in bytes.
        checksum_sha256: The hex SHA-256 digest of the stored bytes.
    """

    key: str
    uri: str
    size: int
    checksum_sha256: str


class StorageError(RuntimeError):
    """Base class for storage errors."""


class ObjectAlreadyExistsError(StorageError):
    """Raised when writing to a key that already exists (immutability, CC-2)."""


class FileTooLargeError(StorageError):
    """Raised when a streamed write exceeds the configured size ceiling (OQ-1.1)."""


class ObjectStorage(abc.ABC):
    """Abstract, immutable object store keyed by string paths."""

    @abc.abstractmethod
    def put(self, key: str, stream: IO[bytes], *, max_bytes: int | None = None) -> StoredObject:
        """Stream ``stream`` to ``key`` (never overwriting), returning its metadata.

        Args:
            key: The destination key.
            stream: A readable binary stream of the object's bytes.
            max_bytes: Optional size ceiling; exceeding it raises ``FileTooLargeError``
                and leaves no partial object.

        Returns:
            The ``StoredObject`` metadata (size + checksum).

        Raises:
            ObjectAlreadyExistsError: If ``key`` already exists.
            FileTooLargeError: If the stream exceeds ``max_bytes``.
        """

    @abc.abstractmethod
    def open(self, key: str) -> IO[bytes]:
        """Open the object at ``key`` for binary reading.

        Args:
            key: The object key.

        Returns:
            A readable binary stream. The caller is responsible for closing it.

        Raises:
            FileNotFoundError: If ``key`` does not exist.
        """

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether an object exists at ``key``."""

    @abc.abstractmethod
    def uri(self, key: str) -> str:
        """Return a backend-specific URI for ``key``."""
