"""add active_mode to user

Revision ID: g3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'g3b4c5d6e7f8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('active_mode', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'active_mode')
