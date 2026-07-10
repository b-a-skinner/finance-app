"""add recurrence to business entries

Revision ID: o1j2k3l4m5n6
Revises: n0i1j2k3l4m5
Create Date: 2026-07-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'o1j2k3l4m5n6'
down_revision: Union[str, None] = 'n0i1j2k3l4m5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('business_income',   sa.Column('recurrence_freq',     sa.String(20), nullable=True))
    op.add_column('business_income',   sa.Column('recurrence_end_date', sa.Date(),     nullable=True))
    op.add_column('business_expenses', sa.Column('recurrence_freq',     sa.String(20), nullable=True))
    op.add_column('business_expenses', sa.Column('recurrence_end_date', sa.Date(),     nullable=True))
    # Existing rows are non-recurring — nullable columns default to NULL, no backfill needed.


def downgrade() -> None:
    op.drop_column('business_income',   'recurrence_end_date')
    op.drop_column('business_income',   'recurrence_freq')
    op.drop_column('business_expenses', 'recurrence_end_date')
    op.drop_column('business_expenses', 'recurrence_freq')
