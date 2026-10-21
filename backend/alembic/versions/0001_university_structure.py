"""university structure

Revision ID: 0001
Revises: 
Create Date: 2026-10-21 12:56:39.858403
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('faculties',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('short_name', sa.String(length=50), nullable=True),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code'),
    sa.UniqueConstraint('name')
    )
    op.create_table('shifts',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('starts_at', sa.Time(), nullable=False),
    sa.Column('ends_at', sa.Time(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('departments',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('faculty_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['faculty_id'], ['faculties.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('faculty_id', 'name')
    )
    op.create_index(op.f('ix_departments_faculty_id'), 'departments', ['faculty_id'], unique=False)
    op.create_table('specialties',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=True),
    sa.Column('level', sa.Enum('bachelor', 'master', name='study_level'), nullable=False),
    sa.Column('duration_years', sa.Integer(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('department_id', 'name', 'level')
    )
    op.create_index(op.f('ix_specialties_department_id'), 'specialties', ['department_id'], unique=False)
    op.create_table('groups',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('course', sa.Integer(), nullable=False),
    sa.Column('student_count', sa.Integer(), nullable=False),
    sa.Column('specialty_id', sa.Integer(), nullable=False),
    sa.Column('shift_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['specialty_id'], ['specialties.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_groups_specialty_id'), 'groups', ['specialty_id'], unique=False)
    op.create_table('subgroups',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('student_count', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'name')
    )
    op.create_index(op.f('ix_subgroups_group_id'), 'subgroups', ['group_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subgroups_group_id'), table_name='subgroups')
    op.drop_table('subgroups')
    op.drop_index(op.f('ix_groups_specialty_id'), table_name='groups')
    op.drop_table('groups')
    op.drop_index(op.f('ix_specialties_department_id'), table_name='specialties')
    op.drop_table('specialties')
    op.drop_index(op.f('ix_departments_faculty_id'), table_name='departments')
    op.drop_table('departments')
    op.drop_table('shifts')
    op.drop_table('faculties')
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS study_level")
