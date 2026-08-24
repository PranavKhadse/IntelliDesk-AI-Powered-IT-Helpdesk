"""add_sla_policies_table

Revision ID: a1b2c3d4e5f6
Revises: 7329deda6b5b
Create Date: 2026-08-24 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7329deda6b5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add sla_policies table."""
    # Use checkfirst/safe table creation
    op.create_table(
        'sla_policies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('first_response_hours', sa.Integer(), nullable=False),
        sa.Column('resolution_hours', sa.Integer(), nullable=False),
        sa.Column('warning_threshold_pct', sa.Integer(), nullable=False),
        sa.Column('escalation_threshold_pct', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sla_policies_id'), 'sla_policies', ['id'], unique=False)
    op.create_index(op.f('ix_sla_policies_priority'), 'sla_policies', ['priority'], unique=False)


def downgrade() -> None:
    """Downgrade schema to drop sla_policies table."""
    op.drop_index(op.f('ix_sla_policies_priority'), table_name='sla_policies')
    op.drop_index(op.f('ix_sla_policies_id'), table_name='sla_policies')
    op.drop_table('sla_policies')
