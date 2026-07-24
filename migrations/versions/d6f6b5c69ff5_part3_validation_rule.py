"""part 3 validation_rule (first-class custom validation rules)

Revision ID: d6f6b5c69ff5
Revises: c5e5a4b58ee4
Create Date: 2026-07-24 01:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd6f6b5c69ff5'
down_revision: str | None = 'c5e5a4b58ee4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'validation_rule',
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['created_by'], ['user.id'],
            name=op.f('fk_validation_rule_created_by_user'), ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenant.id'],
            name=op.f('fk_validation_rule_tenant_id_tenant'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_validation_rule')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_validation_rule_name'),
    )
    with op.batch_alter_table('validation_rule', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_validation_rule_tenant_id'), ['tenant_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('validation_rule', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_validation_rule_tenant_id'))
    op.drop_table('validation_rule')
