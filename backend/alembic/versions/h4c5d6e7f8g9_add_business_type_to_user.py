"""add business_type to user

Revision ID: h4c5d6e7f8g9
Revises: g3b4c5d6e7f8
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'h4c5d6e7f8g9'
down_revision = 'g3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('business_type', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'business_type')
