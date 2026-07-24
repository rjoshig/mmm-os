"""phase 16 stack + stack_row (Gold layer, ADR-012)

Revision ID: a3c3e2f36cc2
Revises: f2b2d1e25bb1
Create Date: 2026-07-24 00:20:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3c3e2f36cc2'
down_revision: str | None = 'f2b2d1e25bb1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'stack',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('lifecycle_status', sa.String(length=16), nullable=False),
        sa.Column('grain', sa.String(length=16), nullable=True),
        sa.Column('reporting_currency', sa.String(length=3), nullable=True),
        sa.Column('reporting_timezone', sa.String(length=64), nullable=True),
        sa.Column('schema_contract', sa.JSON(), nullable=False),
        sa.Column('source_job_ids', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('cloned_from', sa.Uuid(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['created_by'], ['user.id'], name=op.f('fk_stack_created_by_user'), ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenant.id'], name=op.f('fk_stack_tenant_id_tenant'), ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_stack')),
    )
    with op.batch_alter_table('stack', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_stack_tenant_id'), ['tenant_id'], unique=False)

    op.create_table(
        'stack_row',
        sa.Column('stack_id', sa.Uuid(), nullable=False),
        sa.Column('stack_version', sa.Integer(), nullable=False),
        sa.Column('source_job_id', sa.Uuid(), nullable=True),
        sa.Column('source_file_id', sa.Uuid(), nullable=True),
        sa.Column('source_sheet', sa.String(length=255), nullable=True),
        sa.Column('source_row', sa.Integer(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['stack_id'], ['stack.id'], name=op.f('fk_stack_row_stack_id_stack'), ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenant.id'],
            name=op.f('fk_stack_row_tenant_id_tenant'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_stack_row')),
    )
    with op.batch_alter_table('stack_row', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_stack_row_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_stack_row_stack_id'), ['stack_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_stack_row_source_job_id'), ['source_job_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('stack_row', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_stack_row_source_job_id'))
        batch_op.drop_index(batch_op.f('ix_stack_row_stack_id'))
        batch_op.drop_index(batch_op.f('ix_stack_row_tenant_id'))
    op.drop_table('stack_row')
    with op.batch_alter_table('stack', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_stack_tenant_id'))
    op.drop_table('stack')
