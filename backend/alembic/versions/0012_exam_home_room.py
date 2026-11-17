"""group home room, exam consultations

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-17 14:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('groups') as b:
        b.add_column(sa.Column('home_room_id', sa.Integer(), nullable=True))
        b.create_foreign_key('fk_groups_home_room', 'rooms', ['home_room_id'], ['id'], ondelete='SET NULL')
    with op.batch_alter_table('exam_sessions') as b:
        b.add_column(sa.Column('consultations', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('exam_sessions') as b:
        b.drop_column('consultations')
    with op.batch_alter_table('groups') as b:
        b.drop_constraint('fk_groups_home_room', type_='foreignkey')
        b.drop_column('home_room_id')
