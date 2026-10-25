"""two-week timetable

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-25 12:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite-de CHECK çalyşmak we sütün goşmak üçin tablisa täzeden gurulýar (batch).
    with op.batch_alter_table('curriculum_items') as batch:
        batch.add_column(sa.Column('biweekly', sa.Integer(), server_default='0', nullable=False))
        batch.drop_constraint('lessons_per_week_positive', type_='check')
        batch.create_check_constraint(
            'lessons_positive', 'lessons_per_week >= 0 AND biweekly >= 0 AND lessons_per_week + biweekly > 0'
        )
    with op.batch_alter_table('timetables') as batch:
        batch.add_column(sa.Column('weeks', sa.Integer(), server_default='1', nullable=False))
        batch.add_column(sa.Column('starts_on', sa.Date(), nullable=True))
        batch.add_column(sa.Column('ends_on', sa.Date(), nullable=True))
    with op.batch_alter_table('timetable_entries') as batch:
        batch.add_column(sa.Column('week', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('timetable_entries') as batch:
        batch.drop_column('week')
    with op.batch_alter_table('timetables') as batch:
        batch.drop_column('ends_on')
        batch.drop_column('starts_on')
        batch.drop_column('weeks')
    with op.batch_alter_table('curriculum_items') as batch:
        batch.drop_constraint('lessons_positive', type_='check')
        batch.create_check_constraint('lessons_per_week_positive', 'lessons_per_week > 0')
        batch.drop_column('biweekly')
