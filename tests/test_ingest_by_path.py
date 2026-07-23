"""Tests for path-based (landing-zone) ingestion (Phase 01.4)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mmm_os.api.main import app
from mmm_os.core.config import Settings, get_settings
from mmm_os.ingestion.landing import (
    LandingFileNotFoundError,
    LandingRootsDisabledError,
    PathNotAllowedError,
    ingest_file_from_path,
    resolve_landing_path,
)
from mmm_os.models import Tenant
from mmm_os.storage.local import LocalObjectStorage

_CSV = b"date,channel,spend\n2026-01-01,Facebook,100\n"


def _landing(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "landing"
    root.mkdir()
    f = root / "spend.csv"
    f.write_bytes(_CSV)
    return root, f


def test_resolve_landing_path_allows_within_root(tmp_path: Path) -> None:
    """A file inside an allowlisted root resolves."""
    root, f = _landing(tmp_path)
    assert resolve_landing_path(str(f), [str(root)]) == f.resolve()


def test_resolve_landing_path_rejects_outside_root(tmp_path: Path) -> None:
    """A file outside every root is rejected."""
    root, _ = _landing(tmp_path)
    outside = tmp_path / "secret.csv"
    outside.write_bytes(_CSV)
    with pytest.raises(PathNotAllowedError):
        resolve_landing_path(str(outside), [str(root)])


def test_resolve_landing_path_rejects_traversal(tmp_path: Path) -> None:
    """Traversal that escapes the root is rejected (canonicalized)."""
    root, _ = _landing(tmp_path)
    (tmp_path / "secret.csv").write_bytes(_CSV)
    with pytest.raises(PathNotAllowedError):
        resolve_landing_path(str(root / ".." / "secret.csv"), [str(root)])


def test_resolve_landing_path_disabled_when_no_roots() -> None:
    """No configured roots means the feature is disabled."""
    with pytest.raises(LandingRootsDisabledError):
        resolve_landing_path("/anything.csv", [])


def test_resolve_landing_path_missing_file(tmp_path: Path) -> None:
    """A path within a root that does not exist is a not-found error."""
    root, _ = _landing(tmp_path)
    with pytest.raises(LandingFileNotFoundError):
        resolve_landing_path(str(root / "nope.csv"), [str(root)])


def test_ingest_file_from_path_creates_file_and_job(
    engine: Engine, storage: LocalObjectStorage, tmp_path: Path
) -> None:
    """Ingesting by path copies bytes into storage and creates file + job."""
    root, f = _landing(tmp_path)
    with Session(engine) as session:
        tenant = Tenant(name="Acme", slug="acme")
        session.add(tenant)
        session.flush()
        file, job = ingest_file_from_path(
            session, storage, tenant_id=tenant.id, path=str(f), roots=[str(root)]
        )
        assert file.filename == "spend.csv"
        assert file.byte_size == len(_CSV)
        assert job.file_id == file.id


def test_ingest_by_path_endpoint_then_process(client: TestClient, tmp_path: Path) -> None:
    """The endpoint ingests an allowlisted path and the file processes like an upload."""
    root, f = _landing(tmp_path)
    app.dependency_overrides[get_settings] = lambda: Settings(ingest_landing_roots=str(root))
    try:
        tenant_id = uuid.uuid4()
        # Outside the root → 400.
        bad = client.post(
            f"/api/v1/tenants/{tenant_id}/files/ingest-by-path",
            json={"path": str(tmp_path / "x.csv")},
        )
        assert bad.status_code == 400, bad.text

        ok = client.post(
            f"/api/v1/tenants/{tenant_id}/files/ingest-by-path", json={"path": str(f)}
        )
        assert ok.status_code == 201, ok.text
        file_id = ok.json()["file"]["id"]

        processed = client.post(f"/api/v1/tenants/{tenant_id}/files/{file_id}/process")
        assert processed.status_code == 200, processed.text
        assert len(processed.json()["sheets"]) == 1
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_ingest_by_path_disabled_by_default(client: TestClient, tmp_path: Path) -> None:
    """With no landing roots configured, ingest-by-path is a clear 400."""
    _, f = _landing(tmp_path)
    app.dependency_overrides[get_settings] = lambda: Settings(ingest_landing_roots="")
    try:
        tenant_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/tenants/{tenant_id}/files/ingest-by-path", json={"path": str(f)}
        )
        assert resp.status_code == 400, resp.text
        assert "disabled" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_settings, None)
