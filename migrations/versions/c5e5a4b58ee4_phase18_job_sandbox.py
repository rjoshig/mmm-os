"""phase 18 job.sandbox flag

Revision ID: c5e5a4b58ee4
Revises: b4d4f3a47dd3
Create Date: 2026-07-24 00:40:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c5e5a4b58ee4'
down_revision: str | None = 'b4d4f3a47dd3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('sandbox', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('sandbox')
