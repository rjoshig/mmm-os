"""SQLAlchemy engine and session factory.

The engine is built from ``BACKEND_DATABASE_URL`` (read via settings) so the
database is swappable SQLite -> Postgres by config only. SQLite needs
``check_same_thread=False`` for use across threads; other dialects get no such
argument.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.core.config import get_settings


def _engine_kwargs(url: str) -> dict[str, object]:
    """Return dialect-appropriate keyword args for ``create_engine``.

    Args:
        url: The SQLAlchemy database URL.

    Returns:
        Keyword arguments to pass to ``create_engine``.
    """
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def create_db_engine() -> Engine:
    """Create the SQLAlchemy engine from application settings.

    Returns:
        A configured SQLAlchemy ``Engine``.
    """
    url = get_settings().backend_database_url
    return create_engine(url, future=True, **_engine_kwargs(url))


engine: Engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Yield a database session (FastAPI dependency).

    Yields:
        A SQLAlchemy ``Session`` that is closed when the request completes.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
