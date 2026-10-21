"""timetables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-21 13:39:44.581932
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('timetables',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('status', sa.Enum('pending', 'running', 'done', 'failed', name='timetable_status'), nullable=False),
    sa.Column('time_limit_seconds', sa.Integer(), nullable=False),
    sa.Column('solver_status', sa.String(length=50), nullable=True),
    sa.Column('issues', sa.JSON(), nullable=False),
    sa.Column('objective', sa.Float(), nullable=True),
    sa.Column('seconds', sa.Float(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('timetable_entries',
    sa.Column('timetable_id', sa.Integer(), nullable=False),
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('time_slot_id', sa.Integer(), nullable=False),
    sa.Column('room_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['assignment_id'], ['teaching_assignments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['time_slot_id'], ['time_slots.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['timetable_id'], ['timetables.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timetable_entries_timetable_id'), 'timetable_entries', ['timetable_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_timetable_entries_timetable_id'), table_name='timetable_entries')
    op.drop_table('timetable_entries')
    op.drop_table('timetables')
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS timetable_status")
