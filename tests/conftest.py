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

from mmm_os.api.deps import get_storage
from mmm_os.api.main import app
from mmm_os.db.base import Base
from mmm_os.db.session import get_session
from mmm_os.storage.local import LocalObjectStorage


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
def client(engine: Engine, storage: LocalObjectStorage) -> Iterator[TestClient]:
    """A TestClient with DB and storage dependencies overridden."""
    testing_session = sessionmaker(bind=engine)

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
