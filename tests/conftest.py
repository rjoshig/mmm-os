"""Shared pytest fixtures: a temp DB, local storage, and a wired TestClient."""

from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.api.deps import get_secret_store_dep, get_storage
from mmm_os.api.main import app
from mmm_os.db.base import Base
from mmm_os.db.session import get_session
from mmm_os.secrets import SecretStore
from mmm_os.secrets.local import LocalEncryptedSecretStore
from mmm_os.storage.local import LocalObjectStorage


@pytest.fixture(autouse=True)
def _isolate_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize LLM env so tests never read a developer's .env or hit a live API.

    ``core.config`` calls ``load_dotenv()`` at import, so a local ``.env`` with
    ``LLM_ENABLED=true`` plus a real key would otherwise bleed into the test process
    and make suggestion tests call the real provider. Tests that exercise the LLM
    set these explicitly.
    """
    for var in ("LLM_ENABLED", "LLM_CONFIG_FILE", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    """A SQLite engine backed by a temp file, with all tables created."""
    eng = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def storage(tmp_path: Path) -> LocalObjectStorage:
    """A local object-storage backend rooted under the test's tmp_path."""
    return LocalObjectStorage(tmp_path / "storage")


@pytest.fixture
def secret_store(tmp_path: Path) -> SecretStore:
    """An encrypted local secret store rooted under the test's tmp_path."""
    return LocalEncryptedSecretStore(tmp_path / "secrets", b"test-master-key")


@pytest.fixture
def client(
    engine: Engine, storage: LocalObjectStorage, secret_store: SecretStore
) -> Iterator[TestClient]:
    """A TestClient with DB, storage, and secret-store dependencies overridden."""
    testing_session = sessionmaker(bind=engine)

    def override_session() -> Iterator[Session]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_secret_store_dep] = lambda: secret_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_xlsx() -> Callable[[dict[str, list[list[object]]]], bytes]:
    """Return a helper that builds an in-memory XLSX from {sheet_name: rows}."""

    def _make(sheets: dict[str, list[list[object]]]) -> bytes:
        workbook = Workbook()
        default = workbook.active
        first = True
        for name, rows in sheets.items():
            worksheet = default if first else workbook.create_sheet()
            worksheet.title = name
            for row in rows:
                worksheet.append(row)
            first = False
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    return _make
