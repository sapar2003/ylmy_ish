"""exam: latest allowed day (group must finish exams by a date)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-18 21:40:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('exams') as b:
        b.add_column(sa.Column('latest_day', sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('exams') as b:
        b.drop_column('latest_day')
