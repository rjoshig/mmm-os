"""SQLAlchemy engine and session factory.

The engine is built from ``BACKEND_DATABASE_URL`` (read via settings) so the
database is swappable SQLite -> Postgres by config only. SQLite needs
``check_same_thread=False`` for use across threads; other dialects get no such
argument.

Per-customer isolation (Slice 7.2): ``get_session`` yields a ``RoutingSession``
that binds to the active customer's engine when the request is routed to a silo
database (see ``db/routing.py``), and to the shared pool engine otherwise.
Control-plane access (auth, customer registry) uses ``get_control_session``, which
always binds the pool.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mmm_os.db.routing import RoutingSession, pool_engine


def create_db_engine() -> Engine:
    """Return the shared pool engine (cached, built from application settings)."""
    return pool_engine()


# The pool engine + a plain session factory bound to it (control plane).
engine: Engine = create_db_engine()
PoolSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# The request session factory: routes to the active customer's engine per request.
SessionLocal = sessionmaker(
    class_=RoutingSession, autoflush=False, expire_on_commit=False
)


def get_session() -> Iterator[Session]:
    """Yield a routed database session (FastAPI dependency).

    Binds to the active customer's silo engine when the request is routed there,
    else to the shared pool engine.

    Yields:
        A SQLAlchemy ``Session`` that is closed when the request completes.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_control_session() -> Iterator[Session]:
    """Yield a session bound to the pool (control-plane) database.

    Used by auth and the customer registry, which must always read the shared pool
    regardless of which customer a request is routed to.

    Yields:
        A pool-bound SQLAlchemy ``Session``, closed when the request completes.
    """
    session = PoolSessionLocal()
    try:
        yield session
    finally:
        session.close()
