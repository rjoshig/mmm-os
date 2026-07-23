"""Local-filesystem object storage backend (development).

Writes go to a temporary ``.part`` file and are atomically renamed into place, so
a reader never sees a partial object and existing keys are never overwritten.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import IO

from mmm_os.storage.base import (
    DEFAULT_CHUNK_SIZE,
    FileTooLargeError,
    ObjectAlreadyExistsError,
    ObjectStorage,
    StoredObject,
)


class LocalObjectStorage(ObjectStorage):
    """Immutable object storage rooted at a local directory."""

    def __init__(self, root: str | Path) -> None:
        """Initialise the backend.

        Args:
            root: The directory under which objects are stored.
        """
        self._root = Path(root)

    def _path(self, key: str) -> Path:
        return self._root / key

    def put(self, key: str, stream: IO[bytes], *, max_bytes: int | None = None) -> StoredObject:
        """Stream bytes to ``key`` in chunks; never overwrite; enforce ``max_bytes``."""
        path = self._path(key)
        if path.exists():
            raise ObjectAlreadyExistsError(f"object already exists: {key!r}")
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_name(path.name + ".part")
        hasher = hashlib.sha256()
        size = 0
        try:
            with tmp.open("wb") as out:
                while True:
                    chunk = stream.read(DEFAULT_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if max_bytes is not None and size > max_bytes:
                        raise FileTooLargeError(
                            f"upload exceeds max_bytes ({max_bytes}) for key {key!r}"
                        )
                    hasher.update(chunk)
                    out.write(chunk)
            tmp.replace(path)  # atomic move into place
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

        return StoredObject(
            key=key, uri=self.uri(key), size=size, checksum_sha256=hasher.hexdigest()
        )

    def open(self, key: str) -> IO[bytes]:
        """Open the object at ``key`` for reading."""
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return path.open("rb")

    def delete(self, key: str) -> bool:
        """Delete the object at ``key`` (retention/erasure exception to CC-2)."""
        path = self._path(key)
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, key: str) -> bool:
        """Return whether the object exists."""
        return self._path(key).exists()

    def uri(self, key: str) -> str:
        """Return a ``file://`` URI for the object."""
        return self._path(key).resolve().as_uri()
