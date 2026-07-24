"""phase 15 cloned_from provenance columns

Revision ID: b4d4f3a47dd3
Revises: a3c3e2f36cc2
Create Date: 2026-07-24 00:30:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4d4f3a47dd3'
down_revision: str | None = 'a3c3e2f36cc2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ('mapping_config', 'rule_set', 'feed_template', 'connector_config')


def upgrade() -> None:
    for table in _TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('cloned_from', sa.Uuid(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column('cloned_from')
