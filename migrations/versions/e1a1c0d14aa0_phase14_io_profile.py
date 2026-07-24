"""phase 14 io_profile (config-driven I/O paths, CC-14)

Revision ID: e1a1c0d14aa0
Revises: 0a2bbd8a0d32
Create Date: 2026-07-24 00:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e1a1c0d14aa0'
down_revision: str | None = '0a2bbd8a0d32'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'io_profile',
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('input_path', sa.String(length=1024), nullable=True),
        sa.Column('output_path', sa.String(length=1024), nullable=True),
        sa.Column('temp_path', sa.String(length=1024), nullable=True),
        sa.Column('archive_path', sa.String(length=1024), nullable=True),
        sa.Column('error_path', sa.String(length=1024), nullable=True),
        sa.Column('reject_path', sa.String(length=1024), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenant.id'],
            name=op.f('fk_io_profile_tenant_id_tenant'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_io_profile')),
    )
    with op.batch_alter_table('io_profile', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_io_profile_tenant_id'), ['tenant_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('io_profile', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_io_profile_tenant_id'))
    op.drop_table('io_profile')
