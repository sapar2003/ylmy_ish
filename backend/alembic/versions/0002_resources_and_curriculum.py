"""resources and curriculum

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21 13:24:30.057737
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('buildings',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('address', sa.String(length=300), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('room_types',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('streams',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('rooms',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('building_id', sa.Integer(), nullable=False),
    sa.Column('room_type_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('capacity > 0', name='room_capacity_positive'),
    sa.ForeignKeyConstraint(['building_id'], ['buildings.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['room_type_id'], ['room_types.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('building_id', 'name')
    )
    op.create_index(op.f('ix_rooms_building_id'), 'rooms', ['building_id'], unique=False)
    op.create_index(op.f('ix_rooms_room_type_id'), 'rooms', ['room_type_id'], unique=False)
    op.create_table('time_slots',
    sa.Column('shift_id', sa.Integer(), nullable=False),
    sa.Column('weekday', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('starts_at', sa.Time(), nullable=False),
    sa.Column('ends_at', sa.Time(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('ends_at > starts_at', name='slot_time_order'),
    sa.CheckConstraint('weekday BETWEEN 1 AND 7', name='weekday_range'),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('shift_id', 'weekday', 'number')
    )
    op.create_index(op.f('ix_time_slots_shift_id'), 'time_slots', ['shift_id'], unique=False)
    op.create_table('subjects',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=True),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('department_id', 'name')
    )
    op.create_index(op.f('ix_subjects_department_id'), 'subjects', ['department_id'], unique=False)
    op.create_table('teachers',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('position', sa.String(length=100), nullable=True),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('max_lessons_per_week', sa.Integer(), nullable=True),
    sa.Column('max_lessons_per_day', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teachers_department_id'), 'teachers', ['department_id'], unique=False)
    op.create_table('teacher_availability',
    sa.Column('teacher_id', sa.Integer(), nullable=False),
    sa.Column('time_slot_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('available', 'preferred', 'unavailable', name='availability_status'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['time_slot_id'], ['time_slots.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('teacher_id', 'time_slot_id')
    )
    op.create_index(op.f('ix_teacher_availability_teacher_id'), 'teacher_availability', ['teacher_id'], unique=False)
    op.create_table('curriculum_items',
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('lesson_type', sa.Enum('lecture', 'practice', 'lab', 'seminar', name='lesson_type'), nullable=False),
    sa.Column('lessons_per_week', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=True),
    sa.Column('stream_id', sa.Integer(), nullable=True),
    sa.Column('split', sa.Boolean(), nullable=False),
    sa.Column('room_type_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('(group_id IS NULL) <> (stream_id IS NULL)', name='group_xor_stream'),
    sa.CheckConstraint('lessons_per_week > 0', name='lessons_per_week_positive'),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['room_type_id'], ['room_types.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_curriculum_items_group_id'), 'curriculum_items', ['group_id'], unique=False)
    op.create_index(op.f('ix_curriculum_items_stream_id'), 'curriculum_items', ['stream_id'], unique=False)
    op.create_index(op.f('ix_curriculum_items_subject_id'), 'curriculum_items', ['subject_id'], unique=False)
    op.create_table('stream_groups',
    sa.Column('stream_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('stream_id', 'group_id')
    )
    op.create_table('teaching_assignments',
    sa.Column('curriculum_item_id', sa.Integer(), nullable=False),
    sa.Column('subgroup_id', sa.Integer(), nullable=True),
    sa.Column('teacher_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['curriculum_item_id'], ['curriculum_items.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['subgroup_id'], ['subgroups.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('curriculum_item_id', 'subgroup_id')
    )
    op.create_index(op.f('ix_teaching_assignments_curriculum_item_id'), 'teaching_assignments', ['curriculum_item_id'], unique=False)
    op.create_index(op.f('ix_teaching_assignments_teacher_id'), 'teaching_assignments', ['teacher_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_teaching_assignments_teacher_id'), table_name='teaching_assignments')
    op.drop_index(op.f('ix_teaching_assignments_curriculum_item_id'), table_name='teaching_assignments')
    op.drop_table('teaching_assignments')
    op.drop_table('stream_groups')
    op.drop_index(op.f('ix_curriculum_items_subject_id'), table_name='curriculum_items')
    op.drop_index(op.f('ix_curriculum_items_stream_id'), table_name='curriculum_items')
    op.drop_index(op.f('ix_curriculum_items_group_id'), table_name='curriculum_items')
    op.drop_table('curriculum_items')
    op.drop_index(op.f('ix_teacher_availability_teacher_id'), table_name='teacher_availability')
    op.drop_table('teacher_availability')
    op.drop_index(op.f('ix_teachers_department_id'), table_name='teachers')
    op.drop_table('teachers')
    op.drop_index(op.f('ix_subjects_department_id'), table_name='subjects')
    op.drop_table('subjects')
    op.drop_index(op.f('ix_time_slots_shift_id'), table_name='time_slots')
    op.drop_table('time_slots')
    op.drop_index(op.f('ix_rooms_room_type_id'), table_name='rooms')
    op.drop_index(op.f('ix_rooms_building_id'), table_name='rooms')
    op.drop_table('rooms')
    op.drop_table('streams')
    op.drop_table('room_types')
    op.drop_table('buildings')
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS availability_status")
        op.execute("DROP TYPE IF EXISTS lesson_type")
