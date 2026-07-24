"""phase 21 schema_extension (tenant extensibility, ADR-015)

Revision ID: f2b2d1e25bb1
Revises: e1a1c0d14aa0
Create Date: 2026-07-24 00:10:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2b2d1e25bb1'
down_revision: str | None = 'e1a1c0d14aa0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'schema_extension',
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('data_type', sa.String(length=16), nullable=False),
        sa.Column('taxonomy_ref', sa.String(length=128), nullable=True),
        sa.Column('validation', sa.Text(), nullable=True),
        sa.Column('layer', sa.String(length=16), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('lifecycle_status', sa.String(length=16), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenant.id'],
            name=op.f('fk_schema_extension_tenant_id_tenant'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_schema_extension')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_schema_extension_name'),
    )
    with op.batch_alter_table('schema_extension', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_schema_extension_tenant_id'), ['tenant_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('schema_extension', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_schema_extension_tenant_id'))
    op.drop_table('schema_extension')
