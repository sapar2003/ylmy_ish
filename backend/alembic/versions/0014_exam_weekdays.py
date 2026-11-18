"""exam: allowed weekdays (e.g. a teacher available only on Saturdays)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-18 15:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('exams') as b:
        b.add_column(sa.Column('weekdays', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('exams') as b:
        b.drop_column('weekdays')
