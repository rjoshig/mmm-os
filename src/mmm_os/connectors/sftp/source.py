"""SFTP file source (Phase 09.3).

SFTP is a **file** source: pull files from a per-tenant remote directory and land
them exactly like uploads (immutably stored, then parsed via ``FileSource``). The
``SftpClient`` seam has a **local-directory** dev backend (mirrors the object-storage
pattern) so the flow is testable without an SFTP server; a real paramiko-backed
client + optional PGP decryption plug in behind the same interface.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

from mmm_os.ingestion.service import ingest_file
from mmm_os.models import File
from mmm_os.storage.base import ObjectStorage


@runtime_checkable
class SftpClient(Protocol):
    """A minimal SFTP client: list + read files under a remote directory."""

    def list_files(self, remote_dir: str) -> list[str]:
        """Return file names available under ``remote_dir``."""
        ...

    def read_file(self, remote_dir: str, name: str) -> bytes:
        """Return the bytes of ``name`` under ``remote_dir``."""
        ...


class LocalDirSftpClient:
    """A dev ``SftpClient`` backed by a local directory (no network)."""

    def __init__(self, root: Path | str) -> None:
        """Root the client at a local directory standing in for the SFTP host."""
        self.root = Path(root)

    def list_files(self, remote_dir: str) -> list[str]:
        """List regular files under ``root/remote_dir``."""
        directory = self.root / remote_dir
        if not directory.is_dir():
            return []
        return sorted(p.name for p in directory.iterdir() if p.is_file())

    def read_file(self, remote_dir: str, name: str) -> bytes:
        """Read a file's bytes from ``root/remote_dir/name``."""
        return (self.root / remote_dir / name).read_bytes()


def pull_sftp(
    session: Session,
    storage: ObjectStorage,
    client: SftpClient,
    *,
    tenant_id: uuid.UUID,
    remote_dir: str,
) -> list[File]:
    """Ingest every file in a tenant's SFTP directory as an immutable upload.

    Returns the created ``File`` records; each can then be processed via the
    normal ``FileSource`` path (CC-9). Idempotency across re-drops is a Phase-09.6
    concern (naming contract, OQ-9.8).
    """
    ingested: list[File] = []
    for name in client.list_files(remote_dir):
        data = client.read_file(remote_dir, name)
        file, _job = ingest_file(
            session,
            storage,
            tenant_id=tenant_id,
            filename=name,
            content_type=None,
            stream=io.BytesIO(data),
        )
        ingested.append(file)
    return ingested
