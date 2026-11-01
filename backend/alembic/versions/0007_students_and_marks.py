"""students and marks

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-01 18:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def _ts():
    return [
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    ]


def upgrade() -> None:
    op.create_table('students',
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('number', sa.String(length=30), nullable=True),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('subgroup_id', sa.Integer(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    *_ts(),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['subgroup_id'], ['subgroups.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_students_group_id'), 'students', ['group_id'], unique=False)
    op.create_index(op.f('ix_students_subgroup_id'), 'students', ['subgroup_id'], unique=False)
    op.create_table('marks',
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('time_slot_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Enum('2', '3', '4', '5', 'gm', name='mark_value'), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    *_ts(),
    sa.ForeignKeyConstraint(['assignment_id'], ['teaching_assignments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['time_slot_id'], ['time_slots.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.UniqueConstraint('assignment_id', 'student_id', 'day', 'time_slot_id'),
    )
    op.create_index(op.f('ix_marks_assignment_id'), 'marks', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_marks_student_id'), 'marks', ['student_id'], unique=False)
    op.create_index(op.f('ix_marks_day'), 'marks', ['day'], unique=False)
    op.create_table('mark_logs',
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('time_slot_id', sa.Integer(), nullable=False),
    sa.Column('old_value', sa.String(length=5), nullable=True),
    sa.Column('new_value', sa.String(length=5), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    *_ts(),
    sa.ForeignKeyConstraint(['assignment_id'], ['teaching_assignments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['time_slot_id'], ['time_slots.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_mark_logs_assignment_id'), 'mark_logs', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_mark_logs_student_id'), 'mark_logs', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_table('mark_logs')
    op.drop_table('marks')
    op.drop_table('students')
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS mark_value")
