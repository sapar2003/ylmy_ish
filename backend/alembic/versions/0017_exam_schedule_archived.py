"""exam schedule: archived flag (old versions hidden from the list)

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-18 22:10:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('exam_schedules') as b:
        b.add_column(sa.Column('archived', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('exam_schedules') as b:
        b.drop_column('archived')
