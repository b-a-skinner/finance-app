"""Add dual-purpose and HMRC simplified-expense fields to business_expenses

Adds fields needed for mileage allowance, home-office flat rate, and
partial-business-use (percentage) expense tracking.

Revision ID: l8g9h0i1j2k3
Revises: k7f8g9h0i1j2
Create Date: 2026-07-09 09:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'l8g9h0i1j2k3'
down_revision = 'k7f8g9h0i1j2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('business_expenses',
        sa.Column('business_use_percent', sa.Integer(), server_default='100', nullable=False))
    op.add_column('business_expenses',
        sa.Column('expense_method', sa.String(50), nullable=True))
    op.add_column('business_expenses',
        sa.Column('home_office_hours_band', sa.String(20), nullable=True))
    op.add_column('business_expenses',
        sa.Column('business_miles', sa.Integer(), nullable=True))
    op.add_column('business_expenses',
        sa.Column('vehicle_type', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('business_expenses', 'vehicle_type')
    op.drop_column('business_expenses', 'business_miles')
    op.drop_column('business_expenses', 'home_office_hours_band')
    op.drop_column('business_expenses', 'expense_method')
    op.drop_column('business_expenses', 'business_use_percent')
