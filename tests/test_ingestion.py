"""Tests for Phase 1.1 object storage and file ingestion."""

from __future__ import annotations

import hashlib
import io
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.api.deps import get_storage
from mmm_os.api.main import app
from mmm_os.core.config import Settings, get_settings
from mmm_os.db.base import Base
from mmm_os.db.session import get_session
from mmm_os.storage.base import FileTooLargeError, ObjectAlreadyExistsError
from mmm_os.storage.local import LocalObjectStorage


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Yield a TestClient wired to a temp DB and local storage under tmp_path."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    storage = LocalObjectStorage(tmp_path / "storage")

    def override_session() -> Iterator[Session]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _read_uri_bytes(uri: str) -> bytes:
    """Read the bytes at a file:// URI."""
    return Path(url2pathname(urlparse(uri).path)).read_bytes()


def test_upload_creates_file_and_job_and_stores_bytes(client: TestClient) -> None:
    """Uploading returns a file + pending job; raw bytes are byte-identical (CC-2)."""
    tenant_id = uuid.uuid4()
    content = b"date,channel,spend\n2026-01-01,Facebook,100\n"

    response = client.post(
        f"/api/v1/tenants/{tenant_id}/files",
        files={"upload": ("data.csv", content, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file"]["filename"] == "data.csv"
    assert body["file"]["byte_size"] == len(content)
    assert body["file"]["checksum_sha256"] == hashlib.sha256(content).hexdigest()
    assert body["file"]["tenant_id"] == str(tenant_id)
    assert body["job"]["status"] == "pending"
    assert body["job"]["file_id"] == body["file"]["id"]

    # Raw bytes retrievable byte-identical to what was uploaded.
    assert _read_uri_bytes(body["file"]["storage_uri"]) == content


def test_oversize_upload_rejected(client: TestClient, tmp_path: Path) -> None:
    """An over-ceiling upload returns 413 and leaves no partial object."""
    tenant_id = uuid.uuid4()
    app.dependency_overrides[get_settings] = lambda: Settings(max_upload_bytes=8)
    try:
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/files",
            files={"upload": ("big.csv", b"0123456789ABCDEF", "text/csv")},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
    # No partial object left behind for this tenant.
    assert not list((tmp_path / "storage").glob(f"{tenant_id}/**/*.part"))


def test_local_storage_is_immutable(tmp_path: Path) -> None:
    """Writing an existing key raises rather than overwriting (CC-2)."""
    storage = LocalObjectStorage(tmp_path)
    storage.put("a/b/c.bin", io.BytesIO(b"first"))
    with pytest.raises(ObjectAlreadyExistsError):
        storage.put("a/b/c.bin", io.BytesIO(b"second"))
    assert storage.open("a/b/c.bin").read() == b"first"


def test_local_storage_size_guard(tmp_path: Path) -> None:
    """Exceeding max_bytes raises and leaves no object or partial file."""
    storage = LocalObjectStorage(tmp_path)
    with pytest.raises(FileTooLargeError):
        storage.put("big.bin", io.BytesIO(b"0123456789"), max_bytes=4)
    assert not storage.exists("big.bin")
    assert not list(tmp_path.glob("*.part"))
