"""users and publishing

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-01 16:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('role', sa.Enum('admin', 'teacher', name='user_role'), nullable=False),
    sa.Column('teacher_id', sa.Integer(), nullable=True),
    sa.Column('must_change_password', sa.Boolean(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username'),
    sa.UniqueConstraint('teacher_id')
    )
    op.create_index(op.f('ix_users_teacher_id'), 'users', ['teacher_id'], unique=False)
    with op.batch_alter_table('timetables') as batch:
        batch.add_column(sa.Column('published', sa.Boolean(), server_default='0', nullable=False))
    with op.batch_alter_table('exam_schedules') as batch:
        batch.add_column(sa.Column('published', sa.Boolean(), server_default='0', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('exam_schedules') as batch:
        batch.drop_column('published')
    with op.batch_alter_table('timetables') as batch:
        batch.drop_column('published')
    op.drop_index(op.f('ix_users_teacher_id'), table_name='users')
    op.drop_table('users')
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS user_role")
