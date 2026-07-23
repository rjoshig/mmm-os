"""Path-based ("landing zone") ingestion (Phase 01.4).

Ingest a file the backend can already reach **by path** instead of a browser
upload, so large files never stream through the browser. Paths are validated
against an allowlist of landing roots (canonicalized, no traversal) — nothing
outside a configured root is reachable — then copied into immutable storage and
handed to the same file+job pipeline as an upload (CC-2).
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from mmm_os.ingestion.service import ingest_file
from mmm_os.models import File, Job
from mmm_os.storage.base import ObjectStorage


class LandingZoneError(Exception):
    """Base error for path-based ingestion problems."""


class LandingRootsDisabledError(LandingZoneError):
    """No landing roots are configured — the feature is disabled."""


class PathNotAllowedError(LandingZoneError):
    """The requested path is outside every allowlisted landing root."""


class LandingFileNotFoundError(LandingZoneError):
    """The requested path does not exist or is not a regular file."""


def resolve_landing_path(path: str, roots: list[str]) -> Path:
    """Validate ``path`` against the allowlisted landing ``roots`` and return it.

    Args:
        path: The requested file path (server-side, within a landing root).
        roots: Allowlisted absolute landing directories (``settings.landing_roots``).

    Returns:
        The canonicalized, validated file path.

    Raises:
        LandingRootsDisabledError: If no landing roots are configured.
        PathNotAllowedError: If the resolved path is outside every root (or traversal).
        LandingFileNotFoundError: If the path does not exist or is not a file.
    """
    if not roots:
        raise LandingRootsDisabledError(
            "path-based ingestion is disabled (no INGEST_LANDING_ROOTS configured)"
        )
    resolved = Path(path).expanduser().resolve(strict=False)
    allowed_roots = [Path(root).expanduser().resolve(strict=False) for root in roots]
    if not any(resolved == root or resolved.is_relative_to(root) for root in allowed_roots):
        raise PathNotAllowedError(f"path {path!r} is not within an allowlisted landing root")
    if not resolved.is_file():
        raise LandingFileNotFoundError(f"path {path!r} does not exist or is not a file")
    return resolved


def ingest_file_from_path(
    session: Session,
    storage: ObjectStorage,
    *,
    tenant_id: uuid.UUID,
    path: str,
    roots: list[str],
    max_bytes: int | None = None,
    created_by: uuid.UUID | None = None,
) -> tuple[File, Job]:
    """Ingest a file by server path (copy into immutable storage; CC-2).

    Reuses the upload pipeline (:func:`ingest_file`) so everything downstream —
    detection, profiling, mapping, transform, validation, output — is identical to
    an uploaded file; only the *entry* differs (no browser transfer).

    Raises:
        LandingZoneError: If the path is disabled/not-allowed/not-found (mapped to
            HTTP status by the router).
    """
    resolved = resolve_landing_path(path, roots)
    content_type = mimetypes.guess_type(resolved.name)[0]
    with resolved.open("rb") as stream:
        return ingest_file(
            session,
            storage,
            tenant_id=tenant_id,
            filename=resolved.name,
            content_type=content_type,
            stream=stream,
            max_bytes=max_bytes,
            created_by=created_by,
        )
