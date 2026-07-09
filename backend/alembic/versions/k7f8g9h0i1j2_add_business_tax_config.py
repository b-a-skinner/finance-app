"""Add business_tax_configs table

Stores HMRC mileage and home-office simplified-expense rates per tax year.
Seeded via seed.py.

Revision ID: k7f8g9h0i1j2
Revises: j6e7f8g9h0i1
Create Date: 2026-07-09 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'k7f8g9h0i1j2'
down_revision = 'j6e7f8g9h0i1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'business_tax_configs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tax_year', sa.String(10), nullable=False, unique=True),
        sa.Column('home_office_band_25_50', sa.Float(), nullable=False),
        sa.Column('home_office_band_51_100', sa.Float(), nullable=False),
        sa.Column('home_office_band_101_plus', sa.Float(), nullable=False),
        sa.Column('mileage_car_van_first', sa.Float(), nullable=False),
        sa.Column('mileage_car_van_over', sa.Float(), nullable=False),
        sa.Column('mileage_motorcycle', sa.Float(), nullable=False),
        sa.Column('mileage_bicycle', sa.Float(), nullable=False),
        sa.Column('mileage_threshold', sa.Integer(), nullable=False),
        sa.Column('source_note', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('business_tax_configs')
