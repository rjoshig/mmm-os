"""Per-customer database engine routing (Slice 7.2).

Isolation model (bridge / tiered SaaS): standard-tier customers share the **pool**
backend database, isolated by row-level ``tenant_id`` scoping (CC-1). An
enterprise-tier customer can opt into a **silo** — a dedicated database whose URL
is held in the ``SecretStore`` (CC-12, never plaintext at rest, never logged). A
request scoped to ``/tenants/{id}/...`` for a silo customer routes its session to
that customer's engine; every other request uses the shared pool engine.

The plumbing is a ``ContextVar`` set for the request duration (by middleware) plus
a ``RoutingSession`` whose ``get_bind`` honors it. Engines are cached by URL so we
never rebuild a pool per request. Routing is gated by
``settings.multi_db_routing_enabled`` and is a no-op otherwise, so the default
single-database deployment (and the test suite) is entirely unaffected.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Mapper, Session

from mmm_os.core.config import get_settings
from mmm_os.db.base import Base
from mmm_os.secrets import SecretStore

# Engines are expensive (connection pools); cache one per URL for the process.
_ENGINES: dict[str, Engine] = {}

# The engine the current request's business queries should bind to. Unset (None)
# means "use the pool engine" — the default for control-plane and standard-tier.
_ROUTED_ENGINE: ContextVar[Engine | None] = ContextVar("routed_engine", default=None)

# Cache of tenant_id -> resolved dedicated DB URL (or None for pool). Invalidated
# when a customer's isolation changes.
_TENANT_URL_CACHE: dict[uuid.UUID, str | None] = {}


def _engine_kwargs(url: str) -> dict[str, object]:
    """Return dialect-appropriate keyword args for ``create_engine``."""
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def get_engine(url: str) -> Engine:
    """Return a cached engine for ``url``, building it on first use."""
    engine = _ENGINES.get(url)
    if engine is None:
        engine = create_engine(url, future=True, **_engine_kwargs(url))
        _ENGINES[url] = engine
    return engine


def pool_engine() -> Engine:
    """Return the shared pool engine (the configured backend database)."""
    return get_engine(get_settings().backend_database_url)


def dedicated_db_secret_name(tenant_id: uuid.UUID) -> str:
    """Return the ``SecretStore`` key holding a customer's dedicated DB URL."""
    return f"tenant/{tenant_id}/database-url"


def get_dedicated_database_url(store: SecretStore, tenant_id: uuid.UUID) -> str | None:
    """Return a customer's dedicated DB URL from the store, or ``None`` if unset."""
    name = dedicated_db_secret_name(tenant_id)
    if not store.exists(name):
        return None
    return store.get(name).decode("utf-8")


def set_dedicated_database_url(store: SecretStore, tenant_id: uuid.UUID, url: str) -> None:
    """Persist a customer's dedicated DB URL in the store and invalidate the cache."""
    store.put(dedicated_db_secret_name(tenant_id), url.encode("utf-8"))
    _TENANT_URL_CACHE.pop(tenant_id, None)


def clear_dedicated_database_url(store: SecretStore, tenant_id: uuid.UUID) -> None:
    """Remove a customer's dedicated DB URL and invalidate the cache."""
    store.delete(dedicated_db_secret_name(tenant_id))
    _TENANT_URL_CACHE.pop(tenant_id, None)


def invalidate_tenant(tenant_id: uuid.UUID) -> None:
    """Drop any cached routing decision for ``tenant_id``."""
    _TENANT_URL_CACHE.pop(tenant_id, None)


def resolve_engine_for_tenant(
    tenant_id: uuid.UUID, *, control_session: Session, store: SecretStore
) -> Engine:
    """Return the engine a request for ``tenant_id`` should bind to.

    Reads the customer's ``isolation_mode`` from the pool (control-plane) via
    ``control_session``. A silo customer with a stored dedicated URL routes to that
    engine; everyone else routes to the pool. Decisions are cached per tenant.

    Args:
        tenant_id: The customer whose request is being routed.
        control_session: A session bound to the pool DB (control plane).
        store: The secret store holding dedicated DB URLs.

    Returns:
        The resolved ``Engine`` (dedicated for silo, else the pool engine).
    """
    if tenant_id not in _TENANT_URL_CACHE:
        # Import here to avoid a circular import at module load.
        from mmm_os.models.tenant import Tenant

        tenant = control_session.get(Tenant, tenant_id)
        url: str | None = None
        if tenant is not None and tenant.isolation_mode == "silo":
            url = get_dedicated_database_url(store, tenant_id)
        _TENANT_URL_CACHE[tenant_id] = url
    url = _TENANT_URL_CACHE[tenant_id]
    return get_engine(url) if url else pool_engine()


def provision_silo_database(url: str) -> Engine:
    """Create all tables on a customer's dedicated database and return its engine.

    Idempotent: ``create_all`` only creates missing tables. Alembic can still stamp
    the dedicated DB in a real deployment; for SQLite silos this bootstraps schema.
    """
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    return engine


class RoutingSession(Session):
    """A session that binds to the request's routed engine, else the pool.

    Overriding ``get_bind`` lets every existing router keep using the same session
    dependency while transparently talking to the active customer's database.
    """

    def get_bind(  # type: ignore[override]
        self,
        mapper: Mapper[object] | None = None,
        clause: object | None = None,
        **kwargs: object,
    ) -> Engine:
        """Return the engine for this unit of work (routed override or pool)."""
        return _ROUTED_ENGINE.get() or pool_engine()


@contextmanager
def use_engine(engine: Engine | None) -> Iterator[None]:
    """Bind the current context to ``engine`` for its duration (then restore)."""
    token = _ROUTED_ENGINE.set(engine)
    try:
        yield
    finally:
        _ROUTED_ENGINE.reset(token)
