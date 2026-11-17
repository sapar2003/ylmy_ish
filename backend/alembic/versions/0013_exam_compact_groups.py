"""exam session: groups placed on the first days without free days

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-17 15:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('exam_sessions') as b:
        b.add_column(sa.Column('compact_group_ids', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    with op.batch_alter_table('exam_sessions') as b:
        b.drop_column('compact_group_ids')
