"""lesson topics and presentations

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-04 14:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('lesson_topics',
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('time_slot_id', sa.Integer(), nullable=False),
    sa.Column('topic', sa.String(length=300), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('file_name', sa.String(length=200), nullable=True),
    sa.Column('file_key', sa.String(length=100), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['assignment_id'], ['teaching_assignments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['time_slot_id'], ['time_slots.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('assignment_id', 'day', 'time_slot_id'),
    )
    op.create_index(op.f('ix_lesson_topics_assignment_id'), 'lesson_topics', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_lesson_topics_day'), 'lesson_topics', ['day'], unique=False)


def downgrade() -> None:
    op.drop_table('lesson_topics')
