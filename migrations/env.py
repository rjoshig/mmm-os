"""Alembic migration environment.

Key portability settings (see CODING_STANDARDS.md / docs/architecture.md):

* The database URL is read from ``BACKEND_DATABASE_URL`` (never hardcoded), so the
  target database is swappable SQLite -> Postgres by config only.
* ``render_as_batch=True`` so SQLite ``ALTER`` works.
* ``target_metadata`` is the app's ``Base.metadata``, which carries the explicit
  naming convention for portable, named indexes/constraints.

No models exist yet, so ``target_metadata`` is currently empty and
``alembic upgrade head`` runs cleanly on an empty base.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importing the models package registers every table on Base.metadata so Alembic
# autogenerate sees the full schema.
from mmm_os import models  # noqa: F401,E402
from mmm_os.core.config import get_settings
from mmm_os.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the database URL from the environment (single source of truth).
config.set_main_option("sqlalchemy.url", get_settings().backend_database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DBAPI connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with a live connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
