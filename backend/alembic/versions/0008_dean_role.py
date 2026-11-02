"""dean role: users.faculty_id

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-02 14:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'dean'")
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('faculty_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_users_faculty_id', 'faculties', ['faculty_id'], ['id'], ondelete='CASCADE')
        batch.create_index('ix_users_faculty_id', ['faculty_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_index('ix_users_faculty_id')
        batch.drop_constraint('fk_users_faculty_id', type_='foreignkey')
        batch.drop_column('faculty_id')
