"""Postgres portability smoke test (Deferred Postgres migration, hardening).

Database portability is a hard requirement: the backend must run on Postgres by
changing only ``BACKEND_DATABASE_URL`` (see architecture §2). SQLite is exercised by
the rest of the suite; this test runs the same stack against a **real Postgres** to
catch dialect leaks (JSON, UUID, timezone-aware datetimes, booleans).

It is skipped unless ``TEST_POSTGRES_URL`` is set, e.g.::

    TEST_POSTGRES_URL=postgresql+psycopg://postgres@localhost:5432/mmm_os_test \
        uv run pytest tests/test_postgres_portability.py

The referenced database is reset (drop_all + create_all) at the start of the test.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.api.deps import get_secret_store_dep, get_storage
from mmm_os.api.main import app
from mmm_os.db.base import Base
from mmm_os.db.session import get_control_session, get_session
from mmm_os.secrets.local import LocalEncryptedSecretStore
from mmm_os.storage.local import LocalObjectStorage

_PG_URL = os.environ.get("TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not _PG_URL, reason="set TEST_POSTGRES_URL to run the Postgres portability test"
)


@pytest.fixture
def pg_client(tmp_path: object) -> Iterator[TestClient]:
    """A TestClient wired to a fresh Postgres schema + local storage/secrets."""
    assert _PG_URL is not None
    engine = create_engine(_PG_URL, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    make = sessionmaker(bind=engine)

    def override_session() -> Iterator[Session]:
        session = make()
        try:
            yield session
        finally:
            session.close()

    storage = LocalObjectStorage(tmp_path / "storage")  # type: ignore[operator]
    secret_store = LocalEncryptedSecretStore(tmp_path / "secrets", b"pg-test")  # type: ignore[operator]
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_control_session] = override_session
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_secret_store_dep] = lambda: secret_store
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_core_flow_on_postgres(pg_client: TestClient) -> None:
    """Onboard a customer, connect a partner (encrypted), and ingest+process a CSV.

    Exercises JSON columns (settings/columns/fixed_fields), UUID PKs, timezone-aware
    timestamps, and booleans across the API stack on real Postgres.
    """
    # Customer registry (platform-level). Postgres enforces the tenant FK (SQLite
    # does not), so tenant-scoped rows must reference a real tenant — use this
    # customer's id as the tenant for everything below.
    created = pg_client.post(
        "/api/v1/customers", json={"name": "PG Co", "tier": "enterprise", "region": "eu"}
    )
    assert created.status_code == 201, created.text
    tid = uuid.UUID(created.json()["id"])

    # Connector config (JSON account_ids/settings) + encrypted credential.
    cfg = pg_client.post(
        f"/api/v1/tenants/{tid}/connector-configs",
        json={"connector_key": "meta", "name": "Meta", "account_ids": ["act_1"]},
    )
    assert cfg.status_code == 201, cfg.text
    cfg_id = cfg.json()["id"]
    cred = pg_client.put(
        f"/api/v1/tenants/{tid}/connector-configs/{cfg_id}/credential",
        json={"token": "tok", "scopes": ["ads_read"]},
    )
    assert cred.status_code == 200 and cred.json()["has_credential"] is True

    # Feed template (JSON fixed_fields/expected_columns).
    tmpl = pg_client.post(
        f"/api/v1/tenants/{tid}/feed-templates",
        json={"name": "Sales", "fmt": "delimited", "expected_columns": ["date", "spend"]},
    )
    assert tmpl.status_code == 201, tmpl.text

    # Ingest + process a CSV (File/Sheet/Profile: JSON columns + datetimes).
    csv_bytes = b"date,channel,spend\n2026-01-01,meta,100\n2026-01-02,meta,120\n"
    upload = pg_client.post(
        f"/api/v1/tenants/{tid}/files",
        files={"upload": ("sales.csv", csv_bytes, "text/csv")},
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["file"]["id"]

    processed = pg_client.post(f"/api/v1/tenants/{tid}/files/{file_id}/process")
    assert processed.status_code == 200, processed.text
    body = processed.json()
    assert body["job"]["status"] == "succeeded"
    assert body["sheets"] and body["sheets"][0]["columns"]

    # Read back the tenant-scoped list (SELECT + JSON round-trip on Postgres).
    files = pg_client.get(f"/api/v1/tenants/{tid}/files")
    assert files.status_code == 200 and len(files.json()) == 1
