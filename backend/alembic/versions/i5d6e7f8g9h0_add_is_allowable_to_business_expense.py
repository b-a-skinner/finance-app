"""add is_allowable to business_expense

Revision ID: i5d6e7f8g9h0
Revises: h4c5d6e7f8g9
Create Date: 2026-07-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'i5d6e7f8g9h0'
down_revision = 'h4c5d6e7f8g9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default='1' ensures existing Phase-1 expenses default to allowable
    op.add_column(
        'business_expenses',
        sa.Column('is_allowable', sa.Boolean(), nullable=False, server_default='1'),
    )


def downgrade() -> None:
    op.drop_column('business_expenses', 'is_allowable')
