"""phone login: teacher/student phones, student role, login codes

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-06 16:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'student'")
    with op.batch_alter_table('teachers') as batch:
        batch.add_column(sa.Column('phone', sa.String(length=20), nullable=True))
        batch.create_unique_constraint('uq_teachers_phone', ['phone'])
    with op.batch_alter_table('students') as batch:
        batch.add_column(sa.Column('phone', sa.String(length=20), nullable=True))
        batch.create_unique_constraint('uq_students_phone', ['phone'])
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('student_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_users_student_id', 'students', ['student_id'], ['id'], ondelete='CASCADE')
        batch.create_unique_constraint('uq_users_student_id', ['student_id'])
    op.create_table('login_codes',
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('code_hash', sa.String(length=200), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_sent_at', sa.DateTime(), nullable=False),
    sa.Column('window_start', sa.DateTime(), nullable=False),
    sa.Column('sent_in_window', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('phone'),
    )


def downgrade() -> None:
    op.drop_table('login_codes')
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('uq_users_student_id', type_='unique')
        batch.drop_constraint('fk_users_student_id', type_='foreignkey')
        batch.drop_column('student_id')
    with op.batch_alter_table('students') as batch:
        batch.drop_constraint('uq_students_phone', type_='unique')
        batch.drop_column('phone')
    with op.batch_alter_table('teachers') as batch:
        batch.drop_constraint('uq_teachers_phone', type_='unique')
        batch.drop_column('phone')
