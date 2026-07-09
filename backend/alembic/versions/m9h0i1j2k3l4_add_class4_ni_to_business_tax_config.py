"""Add Class 4 and Class 2 NI fields to business_tax_configs.

Revision ID: m9h0i1j2k3l4
Revises: l8g9h0i1j2k3
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'm9h0i1j2k3l4'
down_revision = 'l8g9h0i1j2k3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('business_tax_configs', sa.Column('class4_lower_limit', sa.Float(), nullable=True))
    op.add_column('business_tax_configs', sa.Column('class4_upper_limit', sa.Float(), nullable=True))
    op.add_column('business_tax_configs', sa.Column('class4_main_rate', sa.Float(), nullable=True))
    op.add_column('business_tax_configs', sa.Column('class4_upper_rate', sa.Float(), nullable=True))
    op.add_column('business_tax_configs', sa.Column('class2_small_profits_threshold', sa.Float(), nullable=True))
    op.add_column('business_tax_configs', sa.Column('class2_weekly_rate', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('business_tax_configs', 'class2_weekly_rate')
    op.drop_column('business_tax_configs', 'class2_small_profits_threshold')
    op.drop_column('business_tax_configs', 'class4_upper_rate')
    op.drop_column('business_tax_configs', 'class4_main_rate')
    op.drop_column('business_tax_configs', 'class4_upper_limit')
    op.drop_column('business_tax_configs', 'class4_lower_limit')
