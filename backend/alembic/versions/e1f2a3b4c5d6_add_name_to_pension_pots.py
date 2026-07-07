"""add name to pension_pots

Revision ID: e1f2a3b4c5d6
Revises: d9e1f2a3b4c5
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6'
down_revision = 'd9e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pension_pots', sa.Column('name', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('pension_pots', 'name')
