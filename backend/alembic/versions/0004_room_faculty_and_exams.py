"""room faculty and exams

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25 12:17:47.716486
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('exam_sessions',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.Enum('midterm', 'final', 'retake', 'state', 'other', name='exam_kind'), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('weekdays', sa.JSON(), nullable=False),
    sa.Column('max_per_day', sa.Integer(), nullable=False),
    sa.Column('rest_days', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('ends_on >= starts_on', name='exam_session_dates'),
    sa.CheckConstraint('max_per_day >= 1', name='exam_max_per_day'),
    sa.CheckConstraint('rest_days >= 0', name='exam_rest_days'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('exam_periods',
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('starts_at', sa.Time(), nullable=False),
    sa.Column('ends_at', sa.Time(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('ends_at > starts_at', name='exam_period_time_order'),
    sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id', 'number')
    )
    op.create_index(op.f('ix_exam_periods_session_id'), 'exam_periods', ['session_id'], unique=False)
    op.create_table('exam_schedules',
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('status', sa.Enum('pending', 'running', 'done', 'failed', name='exam_schedule_status'), nullable=False),
    sa.Column('time_limit_seconds', sa.Integer(), nullable=False),
    sa.Column('solver_status', sa.String(length=50), nullable=True),
    sa.Column('issues', sa.JSON(), nullable=False),
    sa.Column('objective', sa.Float(), nullable=True),
    sa.Column('seconds', sa.Float(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_schedules_session_id'), 'exam_schedules', ['session_id'], unique=False)
    op.create_table('exams',
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=True),
    sa.Column('stream_id', sa.Integer(), nullable=True),
    sa.Column('examiner_id', sa.Integer(), nullable=False),
    sa.Column('assistant_id', sa.Integer(), nullable=True),
    sa.Column('room_type_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('(group_id IS NULL) <> (stream_id IS NULL)', name='exam_group_xor_stream'),
    sa.CheckConstraint('assistant_id IS NULL OR assistant_id <> examiner_id', name='exam_two_teachers'),
    sa.ForeignKeyConstraint(['assistant_id'], ['teachers.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['examiner_id'], ['teachers.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['room_type_id'], ['room_types.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exams_assistant_id'), 'exams', ['assistant_id'], unique=False)
    op.create_index(op.f('ix_exams_examiner_id'), 'exams', ['examiner_id'], unique=False)
    op.create_index(op.f('ix_exams_group_id'), 'exams', ['group_id'], unique=False)
    op.create_index(op.f('ix_exams_session_id'), 'exams', ['session_id'], unique=False)
    op.create_index(op.f('ix_exams_stream_id'), 'exams', ['stream_id'], unique=False)
    op.create_index(op.f('ix_exams_subject_id'), 'exams', ['subject_id'], unique=False)
    op.create_table('exam_entries',
    sa.Column('schedule_id', sa.Integer(), nullable=False),
    sa.Column('exam_id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('period_id', sa.Integer(), nullable=False),
    sa.Column('room_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['period_id'], ['exam_periods.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['schedule_id'], ['exam_schedules.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_entries_schedule_id'), 'exam_entries', ['schedule_id'], unique=False)
    # SQLite-de daşary açar goşmak üçin tablisa täzeden gurulýar (batch).
    with op.batch_alter_table('rooms') as batch:
        batch.add_column(sa.Column('faculty_id', sa.Integer(), nullable=True))
        batch.create_index('ix_rooms_faculty_id', ['faculty_id'], unique=False)
        batch.create_foreign_key('fk_rooms_faculty_id', 'faculties', ['faculty_id'], ['id'], ondelete='RESTRICT')


def downgrade() -> None:
    with op.batch_alter_table('rooms') as batch:
        batch.drop_constraint('fk_rooms_faculty_id', type_='foreignkey')
        batch.drop_index('ix_rooms_faculty_id')
        batch.drop_column('faculty_id')
    op.drop_index(op.f('ix_exam_entries_schedule_id'), table_name='exam_entries')
    op.drop_table('exam_entries')
    op.drop_index(op.f('ix_exams_subject_id'), table_name='exams')
    op.drop_index(op.f('ix_exams_stream_id'), table_name='exams')
    op.drop_index(op.f('ix_exams_session_id'), table_name='exams')
    op.drop_index(op.f('ix_exams_group_id'), table_name='exams')
    op.drop_index(op.f('ix_exams_examiner_id'), table_name='exams')
    op.drop_index(op.f('ix_exams_assistant_id'), table_name='exams')
    op.drop_table('exams')
    op.drop_index(op.f('ix_exam_schedules_session_id'), table_name='exam_schedules')
    op.drop_table('exam_schedules')
    op.drop_index(op.f('ix_exam_periods_session_id'), table_name='exam_periods')
    op.drop_table('exam_periods')
    op.drop_table('exam_sessions')
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS exam_schedule_status")
        op.execute("DROP TYPE IF EXISTS exam_kind")
