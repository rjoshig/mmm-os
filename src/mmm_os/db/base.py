"""SQLAlchemy declarative base and portable metadata naming convention.

A ``MetaData`` naming convention names every index and constraint explicitly,
which is a prerequisite for portable Alembic migrations across SQLite and
Postgres (see ``CODING_STANDARDS.md`` — Database portability).

No ORM models are defined yet — they arrive in Phase 0's data-model work. Models
MUST import ``Base`` from here so their tables share this metadata.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Explicit naming convention for constraints/indexes -> portable migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Typed declarative base for all ORM models.

    All models subclass this so their tables share a single ``MetaData`` with the
    portable naming convention above.
    """

    metadata = metadata
