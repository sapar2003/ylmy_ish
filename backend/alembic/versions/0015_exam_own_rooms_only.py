"""exam session: use only each faculty's own rooms

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-18 21:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('exam_sessions') as b:
        b.add_column(sa.Column('own_rooms_only', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('exam_sessions') as b:
        b.drop_column('own_rooms_only')
